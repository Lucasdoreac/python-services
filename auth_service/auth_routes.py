import os
from functools import wraps

import requests
from flasgger import swag_from
from flask import Blueprint, jsonify, request, render_template
from auth_service.controller import AuthenticationController
from auth_service.swagger_docs import get_swagger_specification

auth_bp = Blueprint('auth', __name__)

def token_required(f):

    """
        Decorator que verifica se o token e o email passados na requisição são válidos.

        Args:
            f (function): Função que será decorada.

        Returns:
            function: Função decorada que executa a verificação antes de chamar a função original.
        """

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


def send_magic_link(email, username, magic_link):
    """
    Sends an email with a magic link for login.

    Args:
        email (str): Recipient's email address.
        username (str): The user’s name.
        magic_link (str): The authentication link.

    Returns:
        Response: HTTP response from the email sending service.
    """
    # Render the HTML template with dynamic data
    minio_icon_url = f"{os.getenv('MINIO_URL')}/labtech/email-icones/magic-link.png"
    html_content = render_template('email/magic_link.html',
                                   username=username,
                                   magic_link=magic_link,
                                   minio_icon_url=minio_icon_url)

    url = f"{os.getenv('CLOUD_FUNCTION_URL')}/send-email"
    payload = {
        'subject': 'Autorização de Acesso',
        'content': html_content,
        'to': [email],
        'is_html': True
    }
    headers = {
        'X-API-Key': os.getenv('CLOUD_FUNCTION_API_KEY'),
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    return response


# API Routes
class AuthRoutes:
    @staticmethod
    @auth_bp.route('/auth/send-link', methods=['POST'])
    @swag_from(get_swagger_specification('auth', 'POST'))
    def auth_mail():
        """
        Endpoint para envio de magic link via email.
        Processa o email recebido como parâmetro, valida o domínio,
        gera o token de autenticação, insere o token na base e envia o email com o link.
        Returns:
            JSON response: Mensagem de sucesso ou erro, com o status HTTP apropriado.
         """

        # inject controller
        authentication_controller = AuthenticationController()
        email = request.args.get('email')
        if not email.endswith('@udf.edu.br'):
            return jsonify({'error': 'Invalid email domain'}), 400
        # Generate hash via the controller
        hash_auth = authentication_controller.generate_hash

        # Save the hash and email in the database
        authentication_controller.insert_token(email, hash_auth)

        # Send the magic link via email
        magic_link = f"{os.getenv('REACT_APP')}/auth/callback?email={email}&hash={hash_auth}"
        if os.getenv('FLASK_ENV') == 'development':
            return jsonify({'magic_link': magic_link}), 201
        try:
            send_response = send_magic_link(email, email.split('@')[0], magic_link)
            if send_response.status_code != 200:
                return jsonify({'error': 'Email sender service unavailable: failed to send email'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 503


        return jsonify({'message': 'Magic link sent successfully'}), 201


        # Send the magic link via email
        magic_link = f"{os.getenv('REACT_APP')}/auth/callback?email={email}&hash={hash_auth}"
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
        """
                Endpoint para validação do token.

                Verifica se o token enviado na requisição é válido.

                Returns:
                    JSON response: Retorna True com status HTTP 200 se o token é válido.
        """

        return jsonify(True), 200