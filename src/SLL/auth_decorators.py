import requests
import os
from flask import request, jsonify
from functools import wraps
from SLL.py_log import AppLogger, LogType, Logmessage


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
            return jsonify({"error": "Email missing"}) if not email else jsonify({"error": "Token missing"}) , 401

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
