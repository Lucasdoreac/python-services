import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger, swag_from
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
