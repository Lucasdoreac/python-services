import os
from dotenv import load_dotenv


class Config:
    load_dotenv()  # Ensure the environment variables are loaded

    # Default configurations
    DEBUG = False
    TESTING = False

    # MongoDB configurations
    MONGO_HOST = os.getenv("MONGO_HOST")
    MONGO_DATABASE = os.getenv("MONGO_DATABASE")
    MONGO_USERNAME = os.getenv("MONGO_USERNAME")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

    # MongoDB URI setup
    MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}/"

    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 5050


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
