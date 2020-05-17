from flask import Flask
from flask_mongoengine import MongoEngine
from config import config

db = MongoEngine()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint)

    return app