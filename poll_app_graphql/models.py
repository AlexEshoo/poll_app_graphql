from . import db
from datetime import datetime
from mongoengine import StringField, EmbeddedDocumentListField, connect, ComplexDateTimeField, ObjectIdField
from bson.objectid import ObjectId


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
    question = StringField(max_length=512)
    choices = EmbeddedDocumentListField(Choice)

    @property
    def vote_count(self):
        return sum(c.vote_count for c in self.choices)


if __name__ == '__main__':
    connection = connect('pollapp', host='localhost', port=27017)

    example = Poll(
        question="What?",
        choices=[
            Choice(text="one", votes=[Vote()]),
            Choice(text="two")
        ]
    )
    example.save()
    print(example.choices[0].votes[0].cast_time)
