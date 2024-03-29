import os
from collections import defaultdict
from datetime import timezone

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.getenv("SECRET_KEY")
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True


class DevelopmentConfig(Config):
    SECRET_KEY = "TEMP"
    MONGODB_SETTINGS = {
        'db': 'pollapp',
        'host': 'localhost',
        'port': 27017,
        "tz_aware": True,
        "tzinfo": timezone.utc
    }


config = defaultdict(DevelopmentConfig,
    development=DevelopmentConfig
)
