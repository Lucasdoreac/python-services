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
        allowed_emails = ["danrley.pereira@cs.udf.edu.br"]
        if not (email.endswith('@udf.edu.br') or email in allowed_emails):
            return jsonify({'error': 'Invalid email domain'}), 400

        # Generate hash via the controller
        hash_auth = authentication_controller.generate_hash

        info = {
            'email':email,
            'token': hash_auth
        }

        url = f"{os.getenv('URL_AUTH')}/auth/insert-token"

        try:
            response = requests.post(url, json=info)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to validate token'}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 503


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

    @staticmethod
    @auth_bp.route('/auth/insert-token', methods=['POST'])
    @swag_from(get_swagger_specification(path='auth', method='POST'))
    def insert():

        """
               Endpoint para inserção de token na base de dados.

               Recebe um JSON com 'email' e 'token', e insere essa informação através do controlador.

               Returns:
                   JSON response: Retorna True com status HTTP 200 se a inserção for bem-sucedida,
                                  ou mensagem de erro com o status apropriado.
        """


        data = request.get_json()
        if not data:
            return jsonify({'erro':'Missing json'}),400

        email = data.get('email')
        hash_auth = data.get('token')

        if not email or not hash_auth:
            return jsonify({'error':'email and hash required'}),400

        authentication_controller = AuthenticationController()
        authentication_controller.insert_token(email, hash_auth)
        return jsonify(True),200