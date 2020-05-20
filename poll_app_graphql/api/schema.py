import graphene
from graphene_mongo import MongoengineObjectType
from ..models import Poll as PollModel
from ..models import Choice as ChoiceModel
from ..models import Vote as VoteModel

from flask import request

from datetime import datetime, timedelta


class Vote(MongoengineObjectType):
    class Meta:
        model = VoteModel
        exclude_fields=("ip_address")


class Choice(MongoengineObjectType):
    class Meta:
        model = ChoiceModel

    vote_count = graphene.Int()


class Poll(MongoengineObjectType):
    class Meta:
        model = PollModel

    vote_count = graphene.Int()


class ChoiceInput(graphene.InputObjectType):
    text = graphene.String(required=True)


class PollInput(graphene.InputObjectType):
    question = graphene.String(required=True)
    choices = graphene.List(ChoiceInput, required=True)
    # voting_start = graphene.DateTime()
    voting_start_in = graphene.Int()  # Time in seconds from submission
    # voting_end = graphene.DateTime()
    voting_end_in = graphene.Int()  # Time in seconds from submission
    # results_available_at = graphene.DateTime()
    results_available_in = graphene.Int()  # Time in seconds from submission


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
            results_available_at=results_available_at
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
