import os
from dotenv import load_dotenv


class Config:
    load_dotenv()  # Ensure the environment variables are loaded

    # Default configurations
    DEBUG = False
    TESTING = False

    # MongoDB configurations
    MONGO_DATABASE = os.getenv("MONGO_DATABASE")
    MONGO_HOST = os.getenv("MONGO_HOST")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    MONGO_USERNAME = os.getenv("MONGO_USERNAME")
    SERVER_NAME = os.getenv("SERVER_NAME", "localhost:5000")
    SERVER_SCHEME = os.getenv("SERVER_SCHEME", "http")
    # É o que o Flask usa nos links _external (aprovar/rejeitar nos e-mails).
    # Antes SERVER_SCHEME não tinha efeito e a produção fixava "http".
    PREFERRED_URL_SCHEME = SERVER_SCHEME

    # MongoDB URI setup. A full URI is useful for local development, where
    # MongoDB normally runs as a Docker service instead of Atlas.
    MONGO_URI = os.getenv("MONGO_URI") or f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}/"

    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 5000


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8000


class TestingConfig(Config):
    TESTING = True


def get_config():
    env = os.getenv("FLASK_ENV", "production")
    if env == "development":
        return DevelopmentConfig()
    elif env == "staging":
        return TestingConfig()
    else:
        return ProductionConfig()
