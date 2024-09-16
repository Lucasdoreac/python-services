from datetime import datetime, timedelta

from DAL.auth_repository import AuthenticationRepository


class AuthenticationController:
    _authentication_instance = None

    def __new__(cls, *args, **kwargs):
        if cls._authentication_instance is None:
            cls._authentication_instance = super(AuthenticationController, cls).__new__(cls)
        return cls._authentication_instance

    def __init__(self):
        self.tokens_repository = AuthenticationRepository()

    def is_token_valid(self, token: str, email: str) -> bool:
        return self.tokens_repository.validate_authentication(email, token)

    def insert_token(self, email: str, token: str) -> str:
        expires_at = datetime.now() + timedelta(days=1)
        return self.tokens_repository.insert_authentication(email, token, expires_at)
