from datetime import datetime, timedelta

from DAL.auth_repository import AuthenticationRepository


class AuthenticationController:
    def __init__(self):
        self.tokens_repository = AuthenticationRepository()

    def is_token_valid(self, token: str, email: str) -> bool:
        return self.tokens_repository.validate_authentication(email, token)

    def insert_token(self, email: str, token: str) -> str:
        expires_at = datetime.now() + timedelta(days=1)
        return self.tokens_repository.insert_authentication(email, token, expires_at)
