import os
from dotenv import load_dotenv


class Config:
    """
        Classe base de configuração que carrega variáveis de ambiente e define as configurações padrão.

        As configurações incluem parâmetros para o MongoDB (nome do banco, host, usuário, senha e URI de conexão)
        e para o servidor (host e porta).

        Atributos:
            DEBUG (bool): Define se o modo debug está ativo (padrão: False).
            TESTING (bool): Define se o modo teste está ativo (padrão: False).
            MONGO_DATABASE (str): Nome do banco de dados MongoDB.
            MONGO_HOST (str): Endereço do host do MongoDB.
            MONGO_PASSWORD (str): Senha para conexão com o MongoDB.
            MONGO_USERNAME (str): Nome de usuário para o MongoDB.
            MONGO_URI (str): URI de conexão com o MongoDB.
            SERVER_HOST (str): Endereço do host do servidor.
            SERVER_PORT (int): Porta do servidor.
        """

    load_dotenv()  # Ensure the environment variables are loaded

    # Default configurations
    DEBUG = False
    TESTING = False

    # MongoDB configurations
    MONGO_DATABASE = os.getenv("MONGO_DATABASE")
    MONGO_HOST = os.getenv("MONGO_HOST")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    MONGO_USERNAME = os.getenv("MONGO_USERNAME")

    # MongoDB URI setup
    MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}/"

    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 5050


class DevelopmentConfig(Config):
    """
        Configuração para o ambiente de desenvolvimento.

        Habilita o modo debug para facilitar a identificação e correção de erros durante o desenvolvimento.
    """

    DEBUG = True


class ProductionConfig(Config):
    """
       Configuração para o ambiente de produção.

       Define configurações específicas para a produção, como a segurança dos cookies de sessão e
       a porta do servidor.
    """

    SESSION_COOKIE_SECURE = True
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8000


class TestingConfig(Config):
    """
        Configuração para o ambiente de testes.

        Habilita o modo de teste, permitindo execuções e validações sem afetar o ambiente de produção.
    """

    TESTING = True


def get_config():
    """
        Retorna a instância de configuração apropriada com base na variável de ambiente FLASK_ENV.

        A lógica define:
            - 'development': retorna DevelopmentConfig.
            - 'staging': retorna TestingConfig.
            - Qualquer outro valor: retorna ProductionConfig.

        Returns:
            Config: Instância de DevelopmentConfig, TestingConfig ou ProductionConfig, conforme o ambiente.
    """

    env = os.getenv("FLASK_ENV", "production")
    if env == "development":
        return DevelopmentConfig()
    elif env == "staging":
        return TestingConfig()
    else:
        return ProductionConfig()
