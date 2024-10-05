from flask import request, jsonify
from abc import ABC, abstractmethod
from functools import wraps

from BLL import AuthenticationController

# List of valid API keys
api_keys = [
    "Grupo02-DoNotFuck0ur4p1",
    "Grupo01_please_weNeedTo_protect0ur4p1",
    "test"
]


# Classe decorator não funciona no flask
class AbstractAuthentication(ABC):
    """
    Abstract class for authentication, providing a template for verifying credentials.
    """

    @abstractmethod
    def verify_credentials(self):
        pass

    def __call__(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if self.verify_credentials():
                return f(*args, **kwargs)
            else:
                return jsonify({"message": "Invalid or missing credentials"}), 403
        return decorated_function


class APIKeyAuth(AbstractAuthentication):
    """
    Class to verify API key authentication for routes.
    """

    def verify_credentials(self):
        # Get the API key from the headers
        api_key = request.headers.get('x-api-key')
        return api_key in api_keys


class TokenAuth(AbstractAuthentication):
    """
    Class to verify Token authentication for routes.
    """

    def verify_credentials(self):
        # Create an instance of the authentication controller
        authentication_controller = AuthenticationController()
        # Validate the token using the authentication controller
        return authentication_controller.is_token_valid(
            token=request.args.get('token'),
            email=request.args.get('email')
        )


# Create a decorator to validate the x-api-key
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if api_key and api_key in api_keys:
            return f(*args, **kwargs)
        else:
            return jsonify({"message": "Invalid or missing API key"}), 403
    return decorated_function


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        authentication_controller = AuthenticationController()
        valid_hash = authentication_controller.is_token_valid(token=request.args.get('token'),
                                                              email=request.args.get('email'))

        if valid_hash:
            return f(*args, **kwargs)
        else:
            return jsonify({"message": "Invalid or missing token"}), 403
    return decorated_function
