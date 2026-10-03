import os
import requests
from flask import Response, jsonify

from SLL import AppLogger, Logmessage, LogType
from SLL.auth_upstream import OK, UNAVAILABLE, call_auth, forward_headers, unavailable_payload


def json_passthrough(response) -> Response:
    """Relay the Auth service's answer, always typed as JSON.

    The Auth only speaks JSON. A body that is not JSON (a platform or proxy page) is never
    relayed with the upstream ``Content-Type``, which would have the browser render it as
    markup; it becomes a JSON 502 instead. An empty body (a 2xx with no content) is not JSON either,
    so it becomes a 502 too. ``Retry-After`` from the Auth is passed through.
    """
    try:
        response.json()
    except (ValueError, AttributeError):
        AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, error="non-JSON answer")
        return Response(
            response=jsonify({"error": "Authentication service returned an unexpected answer"}).get_data(as_text=True),
            status=502,
            content_type="application/json",
        )
    relayed = Response(response=response.text, status=response.status_code, content_type="application/json")
    retry_after = (getattr(response, "headers", None) or {}).get("Retry-After")
    if retry_after:  # e.g. the Auth's 429: the client needs to know when to try again
        relayed.headers["Retry-After"] = str(retry_after)
    return relayed


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
            return json_passthrough(response)
        except requests.exceptions.RequestException as e:
            AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, error=type(e).__name__)
            return Response(
                response=jsonify({"error": "Service unavailable"}).get_data(as_text=True),
                status=503,
                content_type="application/json"
            )

    @staticmethod
    def logout(email: str, token: str) -> Response:
        """Ask the Auth service to delete this session (204), without ever echoing the token."""
        url = f"{os.getenv('URL_AUTH')}/auth/logout"
        outcome, response = call_auth("POST", url, json={"email": email, "token": token},
                                      retry_read_timeouts=False)
        if outcome == UNAVAILABLE:
            AppLogger.log(Logmessage.AUTH_SERVICE_UNAVAILABLE, LogType.ERROR, email=email)
            return Response(
                response=jsonify(unavailable_payload(response)).get_data(as_text=True),
                status=503,
                headers={"Retry-After": "10"},
                content_type="application/json",
            )
        if outcome == OK:
            return Response(status=204)
        # a refusal from the Auth (for example its rate limit): relay it as the exchange does
        return Response(
            response=response.text,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json'),
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
        return json_passthrough(response)
