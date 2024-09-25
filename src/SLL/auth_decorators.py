# auth_decorators.py
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

# class AbstractAuthentication(ABC):
#     """
#     Abstract class to enforce API key authentication for routes.
#     """
#
#     def __call__(self, *args, **kwargs):
#         """
#         Verifies the API key before allowing access to the route.
#         """
#         api_key = request.args.get('x-api-key')
#         if api_key in api_keys:
#             print("API key is valid.")
#             return self.verify_api_key(*args, **kwargs)
#         else:
#             return jsonify({"message": "Invalid token"}), 403


# Create a decorator to validate the x-api-key
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the API key from the headers
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
