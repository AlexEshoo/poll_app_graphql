import graphene
from graphene_mongo import MongoengineObjectType
from ..models import Poll as PollModel
from ..models import Choice as ChoiceModel
from ..models import Vote as VoteModel

from datetime import datetime, timedelta


class Vote(MongoengineObjectType):
    class Meta:
        model = VoteModel


class Choice(MongoengineObjectType):
    vote_count = graphene.Int()

    class Meta:
        model = ChoiceModel


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


class Query(graphene.ObjectType):
    polls = graphene.List(Poll)

    def resolve_polls(self, info):
        return list(PollModel.objects.all())


class Mutation(graphene.ObjectType):
    create_poll = CreatePoll.Field()


schema = graphene.Schema(
    query=Query,
    mutation=Mutation
)
