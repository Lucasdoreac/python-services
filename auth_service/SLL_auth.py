import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger, swag_from
from auth_routes import AuthenticationController
from functools import wraps


# create app
def create_app(config_class):
    app = Flask(__name__)
    swagger = Swagger(app)
    app.config.from_object(config_class)
    CORS(app)

    from auth_service.mongo import MongoDBConnectionFactory
    # Load MongoDB Factory
    MongoDBConnectionFactory.init_app(app.config['MONGO_URI'], app.config['MONGO_DATABASE'])

    from auth_service.auth_routes import auth_bp

    # Blueprints register
    app.register_blueprint(auth_bp)

    # Health check
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify(True)

    return app


def send_magic_link(email, username, magic_link):
    """ Sends a magic link email via the cloud function. """
    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send_email"
    payload = {
        'subject': 'Login Authorization',
        'content': f"Hello {username}, use this link to login: {magic_link}",
        'to': [email],
        'is_html': False
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    return response
