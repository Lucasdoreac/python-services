from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger, swag_from
from .swagger_docs import get_swagger_specification


# App Factory
def create_app(config_class):
    app = Flask(__name__)
    swagger = Swagger(app)
    app.config.from_object(config_class)
    CORS(app)

    # Falha rápido na subida se EMAIL_DRY_RUN=false sem destinatários/URL/chave.
    from settings import get_email_settings
    get_email_settings()

    from DAL import MongoDBConnectionFactory
    # Load MongoDB Factory
    MongoDBConnectionFactory.init_app(app.config['MONGO_URI'], app.config['MONGO_DATABASE'])

    # Índice único de reserva ativa (sala, início): a única proteção atômica
    # contra reserva dupla simultânea. Não derruba o boot se falhar (ex.: banco
    # antigo já com duplicatas) — mas avisa alto, porque sem ele a proteção some.
    from DAL import ReservationManager
    try:
        ReservationManager.ensure_indexes()
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).error("Índice único de reservas NÃO criado: %s", exc)

    from .auth_routes import auth_bp
    from .reservation_routes import reservation_bp
    from .events_routes import events_bp
    from .types_routes import types_bp
    from .resource_routes import resources_bp
    from .administration_approval import templates_bp
    
    # Blueprints register
    app.register_blueprint(auth_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(types_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(templates_bp)

    # Health check
    @app.route('/health', methods=['GET'])
    @swag_from(get_swagger_specification('/health'))
    def health():
        return jsonify(True)

    return app
