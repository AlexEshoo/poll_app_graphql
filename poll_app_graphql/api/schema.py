import graphene
from graphene_mongo import MongoengineObjectType
from ..models import Poll as PollModel
from ..models import Choice as ChoiceModel
from ..models import Vote as VoteModel


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
    voting_start = graphene.DateTime()
    voting_end = graphene.DateTime()
    results_available_at = graphene.DateTime()


class CreatePoll(graphene.Mutation):
    class Arguments:
        poll_data = PollInput(required=True)

    Output = Poll  # https://github.com/graphql-python/graphene/issues/543#issuecomment-357668150

    def mutate(self, info, poll_data):
        poll = PollModel(
            question=poll_data.question,
            choices=poll_data.choices
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
