from . import db
from . import login_manager
from datetime import datetime, timezone
from functools import partial
from mongoengine import StringField, EmbeddedDocumentListField, DateTimeField, ObjectIdField, IntField, ReferenceField, ListField
from mongoengine import ValidationError as MongoEngineValidationError
from bson.objectid import ObjectId
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin


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
    cast_time = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    ip_address = StringField()  # validation not needed since always populated by flask request proxy (?)
    user = ReferenceField("User")


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

    @property
    def unique_ip_address_voters(self):
        return set(v.ip_address for v in self.votes)

    @property
    def unique_user_voters(self):
        return set(v.user for v in self.votes)


class Poll(db.Document):
    # id is implicit
    created_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    created_by = ReferenceField("User")
    voting_start = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    voting_end = DateTimeField(default=None, null=True)
    results_available_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    question = StringField(max_length=512)
    choices = EmbeddedDocumentListField(Choice)
    duplicate_vote_protection_mode = IntField()
    selection_limit = IntField(default=1, null=True)

    @property
    def vote_count(self):
        return sum(c.vote_count for c in self.choices)

    @property
    def results_available(self):
        return datetime.now(timezone.utc) > self.results_available_at

    @property
    def voting_is_closed(self):
        if self.voting_end:
            return datetime.now(timezone.utc) > self.voting_end

        return False

    @property
    def unique_ip_address_voters(self):
        unique = set()
        for choice in self.choices:
            unique.update(choice.unique_ip_address_voters)
        return unique

    @property
    def unique_user_voters(self):
        unique = set()
        for choice in self.choices:
            unique.update(choice.unique_user_voters)
        return unique

    def clean(self):
        if self.voting_end and self.voting_end < self.voting_start:
            raise ValidationError("Voting End Time cannot be before Voting Start Time.")
        if self.results_available_at < self.created_at:
            self.results_available_at = self.created_at
        if len(self.choices) < 2:
            raise ValidationError("Poll must have at least 2 choices.")


class User(db.Document, UserMixin):
    joined_at = DateTimeField(default=partial(datetime.now, tz=timezone.utc))
    username = StringField(max_length=32, unique=True)
    password_hash = StringField()
    created_polls = ListField(ReferenceField(Poll))

    @property
    def password(self):
        raise AttributeError("Passwords are not stored.")

    @password.setter
    def password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def verify_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=user_id).first()
