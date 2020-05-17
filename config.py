import os
from collections import defaultdict

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.getenv("SECRET_KEY")


class DevelopmentConfig(Config):
    SECRET_KEY = "TEMP"
    MONGODB_SETTINGS = {
        'db': 'pollapp',
        'host': 'localhost',
        'port': 27017
    }


config = defaultdict(DevelopmentConfig,
    development=DevelopmentConfig
)
