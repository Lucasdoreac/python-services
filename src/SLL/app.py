from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger, swag_from
from .swagger_docs import get_swagger_specification


# App Factory
def create_app(config_class):
    from .startup_checks import require_internal_api_key
    require_internal_api_key()
    from .security_headers import apply_security_headers, docs_enabled
    app = Flask(__name__)
    if docs_enabled():
        Swagger(app)
    app.after_request(apply_security_headers)
    app.config.from_object(config_class)
    from .security_headers import cors_origins
    CORS(app, origins=cors_origins(), supports_credentials=False)

    from DAL import MongoDBConnectionFactory
    # Load MongoDB Factory
    MongoDBConnectionFactory.init_app(app.config['MONGO_URI'], app.config['MONGO_DATABASE'])

    # Preserve the database-level duplicate reservation guard used in
    # Production. Existing duplicate data can prevent index creation, so log
    # the failure without making the whole API unavailable.
    from DAL import ReservationManager
    try:
        ReservationManager.ensure_indexes()
    except Exception as error:
        import logging
        # Class name only: a traceback would carry the driver message (URIs, values).
        logging.getLogger(__name__).error(
            "Could not create the active-reservation unique index (%s)",
            type(error).__name__,
        )

    from .auth_routes import auth_bp
    from .reservation_routes import reservation_bp
    from .events_routes import events_bp
    from .types_routes import types_bp
    from .resource_routes import resources_bp
    from .administration_approval import templates_bp
    from .email_routes import email_bp
    
    # Blueprints register
    app.register_blueprint(auth_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(types_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(email_bp)

    # Health check
    @app.route('/health', methods=['GET'])
    @swag_from(get_swagger_specification('/health'))
    def health():
        return jsonify(True)

    return app
