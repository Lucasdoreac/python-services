import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger, swag_from
from functools import wraps


# create app
def create_app(config_class):
    """
        Cria e configura a aplicação Flask.

        Esta função realiza as seguintes tarefas:
          - Instancia a aplicação Flask.
          - Configura o Swagger para documentação da API.
          - Carrega as configurações a partir da classe de configuração fornecida.
          - Habilita o CORS na aplicação.
          - Inicializa a conexão com o MongoDB utilizando a fábrica de conexão.
          - Registra os blueprints dos endpoints (por exemplo, os endpoints de autenticação).
          - Define um endpoint de health check para monitorar se a aplicação está ativa.

        Args:
            config_class (class): Classe de configuração com os parâmetros da aplicação.

        Returns:
            Flask: Instância configurada da aplicação Flask.
    """

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
        """
                Endpoint de Health Check.

                Este endpoint retorna um valor booleano para indicar que a aplicação está ativa.

                Returns:
                    JSON: Um JSON contendo True, indicando que o serviço está funcionando.
        """

        return jsonify(True)

    return app
