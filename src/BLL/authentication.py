import os
import requests
from flask import Response, jsonify

from SLL import AppLogger, Logmessage, LogType


class AuthenticationController:
    _authentication_instance = None

    def __new__(cls, *args, **kwargs):
        if cls._authentication_instance is None:
            cls._authentication_instance = super(AuthenticationController, cls).__new__(cls)
        return cls._authentication_instance

    @staticmethod
    def is_token_valid(token: str, email: str) -> bool:
        url = f"{os.getenv('URL_AUTH')}/auth/validate"
        response = requests.get(url, params={"email": email, "token": token})
        if response.status_code == 200:
            return True
        return False

    @staticmethod
    def insert_token(email: str) -> Response:
        url = f"{os.getenv('URL_AUTH')}/auth/send-link"
        try:
            # Make the request to the internal authentication API
            response = requests.post(url, params={"email": email})

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
