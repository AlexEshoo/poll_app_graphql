from . import db
from datetime import datetime
from mongoengine import StringField, EmbeddedDocumentListField, ComplexDateTimeField, ObjectIdField, IntField
from mongoengine import ValidationError as MongoEngineValidationError
from bson.objectid import ObjectId
from enum import Enum

class DuplicateVoteProtectionMode(Enum):
    NONE = 0
    COOKIE = 1
    IP_ADDRESS = 2
    LOGIN = 3

class SimpleError(Exception):
    def __init__(self, message):
        self.message = message

ValidationError = SimpleError
# ValidationError = MongoEngineValidationError

class Vote(db.EmbeddedDocument):
    id = ObjectIdField(required=True, default=ObjectId)
    cast_time = ComplexDateTimeField(default=datetime.utcnow)
    ip_address = StringField()  # validation not needed since always populated by flask request proxy (?)


class Choice(db.EmbeddedDocument):
    id = ObjectIdField(required=True, default=ObjectId)
    text = StringField(max_length=256)
    votes = EmbeddedDocumentListField(Vote, default=[])

    @property
    def vote_count(self):
        return self.votes.count()

    @property
    def poll(self):
        return self._instance  # Returns the parent for the EmbeddedDocument


class Poll(db.Document):
    # id is implicit
    created_at = ComplexDateTimeField(default=datetime.utcnow)
    voting_start = ComplexDateTimeField(default=datetime.utcnow)
    voting_end = ComplexDateTimeField(default=None, null=True)
    results_available_at = ComplexDateTimeField(default=datetime.utcnow)
    question = StringField(max_length=512)
    choices = EmbeddedDocumentListField(Choice)
    duplicate_vote_protection_mode = IntField()

    @property
    def vote_count(self):
        return sum(c.vote_count for c in self.choices)

    @property
    def results_available(self):
        return datetime.utcnow() > self.results_available_at

    def clean(self):
        if self.voting_end and self.voting_end < self.voting_start:
            raise ValidationError("Voting End Time cannot be before Voting Start Time.")
        if self.results_available_at < self.created_at:
            self.results_available_at = self.created_at
        if len(self.choices) < 2:
            raise ValidationError("Poll must have at least 2 choices.")

