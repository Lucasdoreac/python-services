from flask import Blueprint, jsonify, request
from flasgger import swag_from
from .swagger_docs import get_swagger_specification
from SLL.auth_decorators import token_required
from BLL import AuthenticationController
from SLL.py_log import AppLogger,LogType,Logmessage
from settings import get_auth_settings

auth_bp = Blueprint('auth', __name__)


class AuthRoutes:
    @staticmethod
    @auth_bp.route('/auth/send-link', methods=['POST'])
    @swag_from(get_swagger_specification('auth', 'POST'))
    def auth_mail():
        authentication_controller = AuthenticationController()
        email = request.args.get('email')
        if not email:
            AppLogger.log(
                Logmessage.MISSING_EMAIL,
                LogType.INFO,
                token=None,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Email missing'}), 400

        if not get_auth_settings().is_allowed(email):
            AppLogger.log(
                Logmessage.INVALID_EMAIL_DOMAIN,
                LogType.INFO,
                email=email,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Invalid email domain'}), 400

        return authentication_controller.insert_token(email)

    @staticmethod
    @auth_bp.route('/auth/validate', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='auth', method='GET'))
    def validate_hash():
        AppLogger.log(Logmessage.TOKEN_VALIDATED, log_type=LogType.INFO, email=request.args.get('email'),
                      token=request.args.get('token'), ip_address=f"{request.remote_addr}")
        return jsonify(True), 200


auth_routes = AuthRoutes()
