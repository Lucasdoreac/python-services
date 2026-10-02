import os
from flask import request, jsonify, make_response
from werkzeug.exceptions import HTTPException
from functools import wraps
from SLL.auth_upstream import DENIED, OK, call_auth, forward_headers, unavailable_payload
from SLL.py_log import AppLogger, LogType, Logmessage, mask_email


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
            )
            return jsonify({"error": "Email missing"}) if not email else jsonify({"error": "Token missing"}) , 401

        outcome, upstream = call_auth("GET", url, params={"email": email, "token": token},
                                      headers=forward_headers(request))
        if outcome == OK:
            status = 500  # stays 500 if the view raises
            try:
                response = make_response(f(*args, **kwargs))
                status = response.status_code
                return response
            except HTTPException as error:  # abort(404): Flask answers with that code, not 500
                status = error.code or 500
                raise
            finally:
                # request.path only: tokens can arrive in the query string. The e-mail is hashed.
                AppLogger.log(
                    Logmessage.REQUEST_AUTHENTICATED,
                    LogType.INFO,
                    email_hash=mask_email(email),
                    method=request.method,
                    path=request.path,
                    status=status,
                )
        if outcome == DENIED:
            AppLogger.log(
                Logmessage.TOKEN_FAILURE,
                LogType.INFO,
                token=token,
                email=email,
            )
            return jsonify({"error": "Token validation failed"}), 403
        AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, email=email)
        response = jsonify(unavailable_payload(upstream))
        response.headers["Retry-After"] = "10"
        return response, 503

    return decorated_function
