import os

from flask import Blueprint, jsonify, request
from flasgger import swag_from
from .swagger_docs import get_swagger_specification
from SLL.auth_decorators import token_required
from BLL import AuthenticationController
from SLL.py_log import AppLogger,LogType,Logmessage
from SLL.email_policy import is_email_allowed
from SLL import client_limits

auth_bp = Blueprint('auth', __name__)


SEND_LINK_PER_CLIENT = 10
EXCHANGE_PER_CLIENT = 60
LOGOUT_PER_CLIENT = 60


class AuthRoutes:
    @staticmethod
    @auth_bp.route('/auth/send-link', methods=['POST'])
    @swag_from(get_swagger_specification('auth', 'POST'))
    def auth_mail():
        authentication_controller = AuthenticationController()
        email = request.args.get('email', '').strip()
        allowed_emails = os.getenv(
            'AUTH_EMAIL_ALLOWLIST', 'danrley.pereira@cs.udf.edu.br'
        )
        if not is_email_allowed(email, allowed_emails):
            AppLogger.log(
                Logmessage.INVALID_EMAIL_DOMAIN,
                LogType.INFO,
                email=email,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Invalid email domain'}), 400

        if client_limits.hit(f"send-link:{client_limits.client_ip(request)}") > SEND_LINK_PER_CLIENT:
            response = jsonify({'error': 'Too many requests; try again later'})
            response.headers['Retry-After'] = str(client_limits.window_seconds())
            return response, 429

        return authentication_controller.insert_token(email)

    @staticmethod
    @auth_bp.route('/auth/exchange', methods=['POST'])
    def exchange_link():
        """Trade the single-use e-mailed link token for a session token."""
        if client_limits.hit(f"exchange:{client_limits.client_ip(request)}") > EXCHANGE_PER_CLIENT:
            response = jsonify({'error': 'Too many requests; try again later'})
            response.headers['Retry-After'] = str(client_limits.window_seconds())
            return response, 429
        body = request.get_json(silent=True)
        body = body if isinstance(body, dict) else {}
        email = str(body.get('email') or '').strip()
        token = body.get('token')
        if not email or not isinstance(token, str) or not token:
            return jsonify({'error': 'email and token are required'}), 400
        return AuthenticationController.exchange_link(email, token)

    @staticmethod
    @auth_bp.route('/auth/logout', methods=['POST'])
    def logout():
        """End the caller's session at the Auth service (the token stops validating at once)."""
        if client_limits.hit(f"logout:{client_limits.client_ip(request)}") > LOGOUT_PER_CLIENT:
            response = jsonify({'error': 'Too many requests; try again later'})
            response.headers['Retry-After'] = str(client_limits.window_seconds())
            return response, 429
        body = request.get_json(silent=True)
        body = body if isinstance(body, dict) else {}
        email = str(body.get('email') or '').strip()
        token = body.get('token')
        if not email or not isinstance(token, str) or not token:
            return jsonify({'error': 'email and token are required'}), 400
        return AuthenticationController.logout(email, token)

    @staticmethod
    @auth_bp.route('/auth/validate', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='auth', method='GET'))
    def validate_hash():
        AppLogger.log(Logmessage.TOKEN_VALIDATED, log_type=LogType.INFO, email=request.args.get('email'),
                      token=request.args.get('token'), ip_address=f"{request.remote_addr}")
        return jsonify(True), 200


auth_routes = AuthRoutes()
