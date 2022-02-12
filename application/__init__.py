from flask import Flask, request, send_from_directory
from application.routes import adp


def create_app():

    app = Flask(__name__)
    app.register_blueprint(adp)

    @app.route("/robots.txt")
    def robots():
        return send_from_directory(app.static_folder, request.path[1:])

    return app