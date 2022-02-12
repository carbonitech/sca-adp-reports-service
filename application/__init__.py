from flask import Flask
from routes import adp


def create_app():

    app = Flask(__name__)
    app.register_blueprint(adp)

    return app