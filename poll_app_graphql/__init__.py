from flask import Flask
from flask_mongoengine import MongoEngine
from config import config
from flask_login import LoginManager

db = MongoEngine()
login_manager = LoginManager()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint)

    return app