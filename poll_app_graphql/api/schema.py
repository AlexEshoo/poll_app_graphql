import graphene
import urllib.parse
from graphql import GraphQLError
from graphene_mongo import MongoengineObjectType
from ..models import Poll as PollModel
from ..models import Choice as ChoiceModel
from ..models import Vote as VoteModel
from ..models import DuplicateVoteProtectionMode
from .utils import Cookie

from flask import request, g

from datetime import datetime, timedelta

DuplicateVoteProtectionModeEnum = graphene.Enum.from_enum(DuplicateVoteProtectionMode)


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
            question=poll_data.question,
            choices=poll_data.choices,
            voting_start=voting_start,
            voting_end=voting_end,
            results_available_at=results_available_at,
            duplicate_vote_protection_mode=poll_data.duplicate_vote_protection_mode
        ).save()

        return poll


class CastVote(graphene.Mutation):
    class Arguments:
        poll_id = graphene.ID()
        choice_id = graphene.ID()

    Output = Poll

    def mutate(self, info, poll_id, choice_id):
        poll = PollModel.objects.get(id=poll_id)
        choice = poll.choices.get(id=choice_id)

        if poll.voting_is_closed:
            raise GraphQLError("Voting is closed for this poll.")

        if poll.duplicate_vote_protection_mode == DuplicateVoteProtectionMode.LOGIN.value:
            ...  # TODO: Require user log in
        elif poll.duplicate_vote_protection_mode == DuplicateVoteProtectionMode.COOKIE.value:
            polls_cookie = urllib.parse.unquote(request.cookies.get("polls", ""))
            voted_polls = polls_cookie.split(',')
            if str(poll.id) in voted_polls:
                raise GraphQLError("You have already voted in this poll")

            voted_polls.append(str(poll.id))
            g.setdefault("cookies", []).append(
                Cookie(
                    "polls",
                    value=urllib.parse.quote(",".join(voted_polls))
                )
            )

        elif poll.duplicate_vote_protection_mode == DuplicateVoteProtectionMode.IP_ADDRESS.value:
            if request.remote_addr in poll.unique_ip_address_voters:
                raise GraphQLError("You may only vote once in this poll from this IP address.")

        choice.votes.append(VoteModel(ip_address=request.remote_addr))
        poll.save()

        return poll


class Query(graphene.ObjectType):
    polls = graphene.List(Poll)
    poll = graphene.Field(Poll, poll_id=graphene.ID(required=True))

    def resolve_polls(self, info):
        return list(PollModel.objects.all())

    def resolve_poll(self, info, poll_id):
        return PollModel.objects.get(id=poll_id)


class Mutation(graphene.ObjectType):
    create_poll = CreatePoll.Field()
    cast_vote = CastVote.Field()


schema = graphene.Schema(
    query=Query,
    mutation=Mutation
)
