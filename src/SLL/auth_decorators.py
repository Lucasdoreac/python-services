import requests
import os
from flask import request, jsonify
from functools import wraps
from SLL.py_log import AppLogger, LogType, Logmessage

# List of valid API keys
api_keys = [
    "Grupo02-DoNotFuck0ur4p1",
    "Grupo01_please_weNeedTo_protect0ur4p1",
    "test"
]


# Create a decorator to validate the x-api-key
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if api_key and api_key in api_keys:
            AppLogger.log(
                Logmessage.API_KEY_VALIDATED,
                LogType.INFO,
                api_key=api_key,
                ip_address=request.remote_addr,
            )
            return f(*args, **kwargs)
        else:
            AppLogger.log(
                Logmessage.MISSING_API_KEY,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({"message": "Invalid or missing API key"}), 403

    return decorated_function


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        url = f"{os.getenv('URL_AUTH')}/auth/validate"

        token = request.headers.get('token') if request.headers.get('token') else request.args.get('token')
        email = request.headers.get('email') if request.headers.get('email') else request.args.get('email')

        if not email or not token:
            AppLogger.log(
                Logmessage.MISSING_EMAIL if not email else Logmessage.MISSING_TOKEN,
                LogType.INFO,
                token=token,
                email=email,
                ip_address=request.remote_addr,
            )
            return jsonify({"error": "Email missing"}), 401

        response = requests.get(url, params={"email": email,
                                             "token": token})
        if response:
            return f(*args, **kwargs)
        else:
            AppLogger.log(
                Logmessage.TOKEN_FAILURE,
                LogType.INFO,
                token=token,
                email=email,
                ip_address=request.remote_addr,
            )
            return jsonify({"error": "Token validation failed"}), 403

    return decorated_function
