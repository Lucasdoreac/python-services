import os
from hashlib import sha256
from flask import Blueprint, jsonify, request
from flasgger import swag_from
from datetime import datetime

from SLL import AppLogger, Logmessage, LogType
from auth_service.controller import AuthenticationController
from functools import wraps
from auth_service.SLL_auth import send_magic_link
from swagger_docs import get_swagger_specification

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        authentication_controller = AuthenticationController()
        valid_hash = authentication_controller.is_token_valid(token=request.args.get('token'),
                                                              email=request.args.get('email'))

        if valid_hash:
            return f(*args, **kwargs)
        else:
            return jsonify({"message": "Invalid or missing token"}), 403
    return decorated_function

# API Routes
class AuthRoutes:
    @staticmethod
    @auth_bp.route('/auth/send-link', methods=['POST'])
    @swag_from(get_swagger_specification('auth', 'POST'))
    def auth_mail():
        # inject controller
        authentication_controller = AuthenticationController()
        email = request.args.get('email')
        if not email.endswith('@udf.edu.br'):
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
                return jsonify({'error': 'Email sender service unavailable: failed to send email'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 503

        return jsonify({'message': 'Magic link sent successfully'}), 201

    @staticmethod
    @auth_bp.route('/auth/validate', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='auth', method='GET'))
    def validate_hash():
        return jsonify(True), 200
