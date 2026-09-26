"""Rotas HTTP para envio de e-mails.

Disponibiliza o endpoint POST /send-email, cumprindo o contrato que o
auth_service e o próprio python-services esperavam da "cloud function".
"""
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from SLL import AppLogger, LogType
from settings import get_email_settings
from .swagger_docs import get_swagger_specification

email_bp = Blueprint('email_routes', __name__)


@email_bp.route('/send-email', methods=['POST'])
@swag_from(get_swagger_specification('/send-email', 'POST'))
def send_email():
    """Recebe solicitações de envio de e-mail e despacha via Brevo ou dry run."""
    settings = get_email_settings()
    api_key = request.headers.get('X-API-Key')

    expected_key = settings.cloud_function_api_key
    if not expected_key or api_key != expected_key:
        return jsonify({"error": "Unauthorized: chave X-API-Key inválida ou ausente"}), 401

    data = request.get_json(silent=True) or {}
    to = data.get('to')
    subject = data.get('subject')
    content = data.get('content')
    is_html = data.get('is_html', True)

    if not to:
        return jsonify({"error": "Campo 'to' é obrigatório"}), 400
    if not subject:
        return jsonify({"error": "Campo 'subject' é obrigatório"}), 400
    if content is None or content == "":
        return jsonify({"error": "Campo 'content' é obrigatório"}), 400

    if isinstance(to, str):
        to = [to]

    if settings.email_dry_run:
        AppLogger.log(
            f"EMAIL_DRY_RUN ligado no /send-email: '{subject}' não enviado para {to}",
            LogType.INFO,
        )
        return jsonify({"status": "sent", "dry_run": True}), 200

    try:
        from .brevo_service import send_brevo_email
        send_brevo_email(to=to, subject=subject, content=content, is_html=is_html)
        return jsonify({"status": "sent"}), 200
    except Exception as exc:
        AppLogger.log(f"Falha ao enviar e-mail para {to}: {exc}", LogType.ERROR)
        return jsonify({"error": f"Falha ao despachar e-mail: {exc}"}), 502
