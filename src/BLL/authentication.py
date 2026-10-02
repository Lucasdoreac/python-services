import os
import requests
from flask import Response, jsonify

from SLL import AppLogger, Logmessage, LogType
from SLL.auth_upstream import OK, UNAVAILABLE, call_auth, forward_headers, unavailable_payload


class AuthenticationController:
    _authentication_instance = None

    def __new__(cls, *args, **kwargs):
        if cls._authentication_instance is None:
            cls._authentication_instance = super(AuthenticationController, cls).__new__(cls)
        return cls._authentication_instance

    @staticmethod
    def is_token_valid(token: str, email: str) -> bool:
        url = f"{os.getenv('URL_AUTH')}/auth/validate"
        outcome, _ = call_auth("GET", url, params={"email": email, "token": token},
                                  headers=forward_headers())
        return outcome == OK

    @staticmethod
    def insert_token(email: str) -> Response:
        url = f"{os.getenv('URL_AUTH')}/auth/send-link"
        try:
            # Make the request to the internal authentication API
            outcome, response = call_auth("POST", url, params={"email": email},
                                          headers=forward_headers(), retry_read_timeouts=False)
            if outcome == UNAVAILABLE:
                AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, email=email)
                return Response(
                    response=jsonify(unavailable_payload(response)).get_data(as_text=True),
                    status=503,
                    headers={"Retry-After": "10"},
                    content_type="application/json",
                )

            # Create a Flask response using the content and status code from the internal API
            flask_response = Response(
                response=response.text,
                status=response.status_code,
                content_type=response.headers.get('Content-Type', 'application/json')
            )
            return flask_response
        except requests.exceptions.RequestException as e:
            AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, error=str(e))
            return Response(
                response=jsonify({"error": "Service unavailable"}).get_data(as_text=True),
                status=503,
                content_type="application/json"
            )

    @staticmethod
    def exchange_link(email: str, token: str) -> Response:
        """Trade the e-mailed link token for a session token at the Auth service."""
        url = f"{os.getenv('URL_AUTH')}/auth/exchange"
        outcome, response = call_auth("POST", url, json={"email": email, "token": token},
                                      headers=forward_headers(), retry_read_timeouts=False)
        if outcome == UNAVAILABLE:
            AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, email=email)
            return Response(
                response=jsonify(unavailable_payload(response)).get_data(as_text=True),
                status=503,
                headers={"Retry-After": "10"},
                content_type="application/json",
            )
        return Response(
            response=response.text,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json'),
        )
