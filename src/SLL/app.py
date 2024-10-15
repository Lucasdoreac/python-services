from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger, swag_from

from configmodule import get_config
from .swagger_docs import get_swagger_specification


# App Factory
def create_app(config_class):
    app = Flask(__name__)
    swagger = Swagger(app)
    app.config.from_object(config_class)
    CORS(app)

    from DAL import MongoDBConnectionFactory
    # Load MongoDB Factory
    MongoDBConnectionFactory.init_app(app.config['MONGO_URI'], app.config['MONGO_DATABASE'])


    from .reservation_routes import reservation_bp
    from .events_routes import events_bp
    from .types_routes import types_bp
    from .resource_routes import resources_bp
    # Blueprints register

    app.register_blueprint(reservation_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(types_bp)
    app.register_blueprint(resources_bp)

    # Health check
    @app.route('/health', methods=['GET'])
    @swag_from(get_swagger_specification('/health'))
    def health():
        return jsonify(True)

    return app
