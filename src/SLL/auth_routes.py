import os
from datetime import datetime
from hashlib import sha256
from flask import Blueprint, jsonify, request
from flasgger import swag_from

from SLL.auth_decorators import token_required
from SLL.email_service import send_magic_link
from BLL import AuthenticationController

auth_bp = Blueprint('auth', __name__)


class AuthRoutes:
    @staticmethod
    @auth_bp.route('/auth/send-link', methods=['POST'])
    @swag_from({
        "summary": "Enviar link de autenticação",
        "description": "Endpoint para enviar um link de autenticação para o email fornecido, apenas emails do domínio '@udf.edu.br' são permitidos.",
        "parameters": [
            {
                "name": "email",
                "in": "query",
                "type": "string",
                "required": True,
                "description": "O email para o qual o link de autenticação será enviado.",
                "example": "usuario@udf.edu.br"
            }
        ],
        "responses": {
            "201": {
                "description": "Link de autenticação enviado com sucesso",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Mensagem de confirmação",
                            "example": "Magic link sent successfully"
                        },
                        "magic_link": {
                            "type": "string",
                            "description": "Link mágico para autenticação",
                            "example": "http://127.0.0.1:5000/auth/callback?email=usuario@udf.edu.br&hash=hash_auth"
                        }
                    }
                }
            },
            "400": {
                "description": "Erro de validação de email",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Mensagem de erro",
                            "example": "Invalid email domain"
                        }
                    }
                }
            },
            "503": {
                "description": "Serviço de envio de email indisponível",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Mensagem de erro",
                            "example": "Email sender service unavailable: failed to send email"
                        }
                    }
                }
            }
        }
    })
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
    @swag_from({
        "summary": "Validar hash de autenticação",
        "description": "Endpoint para validar o hash de autenticação enviado para o email.",
        "parameters": [
            {
                "name": "token",
                "in": "query",
                "type": "string",
                "required": True,
                "description": "O token de autenticação enviado no link.",
                "example": "hash_auth"
            },
            {
                "name": "email",
                "in": "query",
                "type": "string",
                "required": True,
                "description": "O email associado ao token de autenticação.",
                "example": "usuario@udf.edu.br"
            }
        ],
        "responses": {
            "200": {
                "description": "Hash validado com sucesso",
                "schema": {
                    "type": "object",
                    "properties": {
                        "valid": {
                            "type": "boolean",
                            "description": "Indica se o hash é válido ou não.",
                            "example": True
                        }
                    }
                }
            },
            "400": {
                "description": "Erro de validação de dados",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Mensagem de erro",
                            "example": "Invalid token or email"
                        }
                    }
                }
            }
        }
    })
    def validate_hash():
        return jsonify(True), 200


auth_routes = AuthRoutes()
