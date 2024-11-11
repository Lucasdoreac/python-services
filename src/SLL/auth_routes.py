import os
from datetime import datetime,date
from hashlib import sha256
from flask import Blueprint, jsonify, request
from flasgger import swag_from
from .swagger_docs import get_swagger_specification
from SLL.auth_decorators import token_required
from SLL.email_service import send_magic_link
from BLL import AuthenticationController
from SLL.py_log import AppLogger,LogType,Logmessage

auth_bp = Blueprint('auth', __name__)


class AuthRoutes:
    @staticmethod
    @auth_bp.route('/auth/send-link', methods=['POST'])
    @swag_from(get_swagger_specification('auth', 'POST'))
    def auth_mail():
        # inject controller
        authentication_controller = AuthenticationController()
        email = request.args.get('email')
        if not email.endswith('@udf.edu.br'):
            AppLogger.log(
                Logmessage.INVALID_EMAIL_DOMAIN,
                LogType.INFO,
                email=email,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Invalid email domain'}), 400

        # Generate hash
        now = datetime.now()
        hash_auth = sha256(str(now).encode()).hexdigest()

        # Save the hash and email in the database
        authentication_controller.insert_token(email, hash_auth)

        # Send the magic link via email
        magic_link = f"http://{request.remote_addr}/auth/callback?email={email}&hash={hash_auth}"
        if os.getenv('FLASK_ENV') == 'development':
            return jsonify({'magic_link': magic_link}), 201
        try:
            send_response = send_magic_link(email, email.split('@')[0], magic_link)
            if send_response.status_code != 200:
                AppLogger.log(
                    Logmessage.FAILED_SEND_EMAIL,
                    LogType.INFO,
                    ip_address=request.remote_addr,
                )
                return jsonify({'error': 'Email sender service unavailable: failed to send email'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 503

        return jsonify({'message': 'Magic link sent successfully'}), 201

    @staticmethod
    @auth_bp.route('/auth/validate', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='auth', method='GET'))
    def validate_hash():
        AppLogger.log(Logmessage.TOKEN_VALIDATED, log_type=LogType.INFO, email=request.args.get('email'),
                      token=request.args.get('token'), ip_address=request.remote_addr)
        return jsonify(True), 200


auth_routes = AuthRoutes()
