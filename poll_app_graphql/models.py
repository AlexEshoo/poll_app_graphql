from . import db
from datetime import datetime
from mongoengine import StringField, EmbeddedDocumentListField, ComplexDateTimeField, ObjectIdField
from mongoengine import ValidationError as MongoEngineValidationError
from bson.objectid import ObjectId


class SimpleError(Exception):
    def __init__(self, message):
        self.message = message

ValidationError = SimpleError
# ValidationError = MongoEngineValidationError

class Vote(db.EmbeddedDocument):
    cast_time = ComplexDateTimeField(default=datetime.utcnow)


class Choice(db.EmbeddedDocument):
    id = ObjectIdField(required=True, default=ObjectId, unique=True, primary_key=True)
    text = StringField(max_length=256)
    votes = EmbeddedDocumentListField(Vote)

    @property
    def vote_count(self):
        return self.votes.count()


class Poll(db.Document):
    # id is implicit
    created_at = ComplexDateTimeField(default=datetime.utcnow)
    voting_start = ComplexDateTimeField(default=datetime.utcnow)
    voting_end = ComplexDateTimeField(default=None, null=True)
    results_available_at = ComplexDateTimeField(default=datetime.utcnow)
    question = StringField(max_length=512)
    choices = EmbeddedDocumentListField(Choice)

    @property
    def vote_count(self):
        return sum(c.vote_count for c in self.choices)

    def clean(self):
        if self.voting_end < self.voting_start:
            raise ValidationError("Voting End Time cannot be before Voting Start Time.")
        if self.results_available_at < self.created_at:
            self.results_available_at = self.created_at
        if len(self.choices) < 2:
            raise ValidationError("Poll must have at least 2 choices.")

