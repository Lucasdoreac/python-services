import os
from flask import request, jsonify
from functools import wraps
from SLL.auth_upstream import DENIED, OK, call_auth, forward_headers, unavailable_payload
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

        outcome, upstream = call_auth("GET", url, params={"email": email, "token": token},
                                      headers=forward_headers(request))
        if outcome == OK:
            return f(*args, **kwargs)
        if outcome == DENIED:
            AppLogger.log(
                Logmessage.TOKEN_FAILURE,
                LogType.INFO,
                token=token,
                email=email,
                ip_address=request.remote_addr,
            )
            return jsonify({"error": "Token validation failed"}), 403
        AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, email=email,
                      ip_address=request.remote_addr)
        response = jsonify(unavailable_payload(upstream))
        response.headers["Retry-After"] = "10"
        return response, 503

    return decorated_function
