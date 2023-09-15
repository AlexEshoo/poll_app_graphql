import graphene
import urllib.parse
from graphql import GraphQLError
from graphene_mongo import MongoengineObjectType
from ..models import Poll as PollModel
from ..models import Choice as ChoiceModel
from ..models import Vote as VoteModel
from ..models import DuplicateVoteProtectionMode
from ..models import User as UserModel
from .utils import Cookie

from flask import request, g
from flask_login import login_user, logout_user, current_user

from mongoengine import NotUniqueError

from datetime import datetime, timedelta

DuplicateVoteProtectionModeEnum = graphene.Enum.from_enum(DuplicateVoteProtectionMode)


class User(MongoengineObjectType):
    class Meta:
        model = UserModel
        exclude_fields = ("password_hash")


class Vote(MongoengineObjectType):
    class Meta:
        model = VoteModel
        exclude_fields = ("ip_address")


class Choice(MongoengineObjectType):
    class Meta:
        model = ChoiceModel

    vote_count = graphene.Int()

    def resolve_vote_count(self, info):
        """
        Overrides the behavior of this query to not return the
        results before they are scheduled to be public
        """
        return self.vote_count if self.poll.results_available else None

    def resolve_votes(self, info):
        return self.votes if self.poll.results_available else None


class Poll(MongoengineObjectType):
    class Meta:
        model = PollModel

    vote_count = graphene.Int()
    duplicate_vote_protection_mode = DuplicateVoteProtectionModeEnum()  # Needed here to parse INT -> ENUM


class ChoiceInput(graphene.InputObjectType):
    text = graphene.String(required=True)


class PollInput(graphene.InputObjectType):
    question = graphene.String(required=True)
    choices = graphene.List(ChoiceInput, required=True)
    voting_start_in = graphene.Int()  # Time in seconds from submission
    voting_end_in = graphene.Int()  # Time in seconds from submission
    results_available_in = graphene.Int()  # Time in seconds from submission
    duplicate_vote_protection_mode = DuplicateVoteProtectionModeEnum()
    selection_limit = graphene.Int()


class CreatePoll(graphene.Mutation):
    class Arguments:
        poll_data = PollInput(required=True)

    Output = Poll  # https://github.com/graphql-python/graphene/issues/543#issuecomment-357668150

    def mutate(self, info, poll_data):
        request_time = datetime.utcnow()
        voting_start = None
        if poll_data.voting_start_in:
            voting_start = request_time + timedelta(seconds=poll_data.voting_start_in)

        voting_end = None
        if poll_data.voting_end_in:
            voting_end = request_time + timedelta(seconds=poll_data.voting_end_in)

        results_available_at = None
        if poll_data.results_available_in:
            results_available_at = request_time + timedelta(seconds=poll_data.results_available_in)

        poll = PollModel(
            created_by=current_user._get_current_object() if not current_user.is_anonymous else None,
            question=poll_data.question,
            choices=poll_data.choices,
            voting_start=voting_start,
            voting_end=voting_end,
            results_available_at=results_available_at,
            duplicate_vote_protection_mode=poll_data.duplicate_vote_protection_mode.value,
            selection_limit=poll_data.selection_limit
        ).save()

        if not current_user.is_anonymous:
            current_user.created_polls.append(poll)
            current_user.save()

        return poll


class SuccessResult(graphene.ObjectType):
    ok = graphene.NonNull(graphene.Boolean)
    fail_reason = graphene.String()


class MutationFailure(graphene.Interface):
    error_message = graphene.String(required=True)


class CastVoteSuccess(graphene.ObjectType):
    votes = graphene.List(Vote)


class CastVoteFailVoteLimit(graphene.ObjectType):
    class Meta:
        interfaces = (MutationFailure,)


class CastVoteFailSelectionLimit(graphene.ObjectType):
    class Meta:
        interfaces = (MutationFailure,)


class CastVoteFailPollClosed(graphene.ObjectType):
    class Meta:
        interfaces = (MutationFailure,)


class CastVoteFailLoginRequired(graphene.ObjectType):
    class Meta:
        interfaces = (MutationFailure,)


class CastVotePayload(graphene.Union):
    class Meta:
        types = (
            CastVoteSuccess,
            CastVoteFailPollClosed,
            CastVoteFailVoteLimit,
            CastVoteFailSelectionLimit,
            CastVoteFailLoginRequired
        )


# noinspection PyArgumentList
class CastVote(graphene.Mutation):
    class Arguments:
        poll_id = graphene.ID(required=True)
        choice_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)

    Output = CastVotePayload

    def mutate(self, info, poll_id, choice_ids):
        poll = PollModel.objects.get(id=poll_id)
        choices = [poll.choices.get(id=id) for id in choice_ids]

        polls_cookie = urllib.parse.unquote(request.cookies.get("polls", ""))
        voted_polls = polls_cookie.split(',')

        if poll.voting_is_closed:
            return CastVoteFailPollClosed(error_message="Voting is closed for this poll")

        if len(choices) > poll.selection_limit:
            return CastVoteFailSelectionLimit(error_message="You may only make {poll.selection_limit} selections.")

        if poll.duplicate_vote_protection_mode == DuplicateVoteProtectionMode.LOGIN.value:
            if current_user.is_anonymous:
                return CastVoteFailLoginRequired(error_message="You must be logged in to vote in this poll.")
            if current_user._get_current_object() in poll.unique_user_voters:
                return CastVoteFailVoteLimit(error_message="You have already voted in this poll")

        elif poll.duplicate_vote_protection_mode == DuplicateVoteProtectionMode.COOKIE.value:
            if str(poll.id) in voted_polls:
                return CastVoteFailVoteLimit(error_message="You have already voted in this poll")

        elif poll.duplicate_vote_protection_mode == DuplicateVoteProtectionMode.IP_ADDRESS.value:
            if request.remote_addr in poll.unique_ip_address_voters:
                return CastVoteFailVoteLimit(error_message="You have already voted in this poll")

        votes = []
        for choice in choices:
            vote = VoteModel(
                ip_address=request.remote_addr,
                user=current_user._get_current_object() if not current_user.is_anonymous else None
            )
            choice.votes.append(vote)
            votes.append(vote)

        poll.save()

        if poll.duplicate_vote_protection_mode == DuplicateVoteProtectionMode.COOKIE.value:
            voted_polls.append(str(poll.id))
            g.setdefault("cookies", []).append(
                Cookie(
                    "polls",
                    value=urllib.parse.quote(",".join(voted_polls))
                )
            )

        return CastVoteSuccess(votes=votes)


# noinspection PyArgumentList
class Login(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
        remember_me = graphene.Boolean(default_value=False)

    Output = SuccessResult

    def mutate(self, info, username, password, remember_me):
        if not current_user.is_anonymous:
            return SuccessResult(ok=False, fail_reason="User is already logged in.")

        user = UserModel.objects(username=username).first()

        if user is None:
            return SuccessResult(ok=False, fail_reason="Username does not exist.")

        if not user.verify_password(password):
            return SuccessResult(ok=False, fail_reason="Password is incorrect.")

        login_user(user, remember=remember_me)
        return SuccessResult(ok=True)


# noinspection PyArgumentList
class Logout(graphene.Mutation):
    Output = SuccessResult

    def mutate(self, info):
        if current_user.is_anonymous:
            return SuccessResult(ok=False, fail_reason="User is not logged in.")

        logout_user()
        return SuccessResult(ok=True)


# noinspection PyArgumentList
class Register(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)

    Output = SuccessResult

    def mutate(self, info, username, password):
        new_user = UserModel(username=username)
        new_user.password = password  # Sets hash internally and discards raw password

        try:
            new_user.save()
        except NotUniqueError:
            return SuccessResult(ok=False, fail_reason="Username is taken.")

        return SuccessResult(ok=True)


class Query(graphene.ObjectType):
    polls = graphene.List(Poll)
    poll = graphene.Field(Poll, poll_id=graphene.ID(required=True))
    me = graphene.Field(User)

    def resolve_polls(self, info):
        return list(PollModel.objects.all())

    def resolve_poll(self, info, poll_id):
        return PollModel.objects.get(id=poll_id)

    def resolve_me(self, info):
        if current_user.is_anonymous:
            return None

        return current_user._get_current_object()


class Mutation(graphene.ObjectType):
    create_poll = CreatePoll.Field()
    cast_vote = CastVote.Field()
    login = Login.Field()
    logout = Logout.Field()
    register = Register.Field()


schema = graphene.Schema(
    query=Query,
    mutation=Mutation
)
