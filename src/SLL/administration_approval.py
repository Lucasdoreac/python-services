import os
from bson import ObjectId
from flask import Blueprint, request, jsonify, render_template
from BLL import send_to_reitoria, send_to_coordenacao, send_event_status, send_reservation_info_to_reitoria
from BLL.index import FlowController
from BLL.send_emails import (InvalidApprovalToken, apply_token_action, send_changes_request,
                             step_for_who, verify_token_from_email)
from SLL.auth_decorators import token_required
from SLL.py_log import AppLogger, LogType, Logmessage
from functools import wraps
from utils.enums import EmailStep

# Create a blueprint for handling templates and related routes.
templates_bp = Blueprint('templates_bp', __name__, template_folder='../templates')


def _step_of_request():
    """Etapa (0 Coordenação, 1 Reitoria) a que o link se refere: `who` ou `step`; None se inválido."""
    if request.endpoint == "templates_bp.request_changes":
        return EmailStep.COORDENACAO.value  # só a Coordenação pede alterações
    who = request.args.get("who")
    if who is not None:
        return step_for_who(who)
    step = request.args.get("step")
    if step is not None and step.isdigit():
        return int(step)
    return None


def check_request(f):
    """O token do link precisa ser ativo e ter sido emitido para este evento e esta etapa.

    Sem correspondência a resposta é 404 e nenhuma decisão é gravada.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tokenId = request.args.get('tokenId')
        eventId = request.args.get('eventId')

        if not (eventId and tokenId):
            return "Not found", 404

        if not verify_token_from_email(tokenId, eventId, _step_of_request()):
            return jsonify({'token': 'Desativado ou Não autorizado'}), 404

        return f(*args, **kwargs)

    return decorated_function


@templates_bp.route('/administration_approval', methods=['GET', 'POST'])
@check_request
def administration_approval():
    eventId = request.args.get('eventId')
    step = request.args.get('step')

    if not step:
        return "Not found", 404
    step = int(step)
    if step == 0:
        if os.getenv("FLASK_ENV") == "development":
            return send_to_coordenacao(eventId)
    elif step == 1:
        if os.getenv("FLASK_ENV") == "development":
            return send_to_reitoria(eventId)


@templates_bp.route('/approve')
@check_request
def approve():
    eventId = request.args.get('eventId')
    who = request.args.get('who')
    token = request.args.get('tokenId')

    try:
        send_event_status(eventId, True, who, token)
    except InvalidApprovalToken:
        return jsonify({'token': 'Desativado ou Não autorizado'}), 404
    if who == "coordenacao":
        if os.getenv("FLASK_ENV") == "development":
            return send_to_reitoria(eventId)
        send_to_reitoria(eventId)
    return "Evento aprovado!"


@templates_bp.route('/reject')
@check_request
def reject():
    eventId = request.args.get('eventId')
    who = request.args.get('who')
    token = request.args.get('tokenId')

    try:
        result = send_event_status(eventId, False, who, token)
    except InvalidApprovalToken:
        return jsonify({'token': 'Desativado ou Não autorizado'}), 404
    if os.getenv("FLASK_ENV") == "development":
        return result
    return "Evento rejeitado!"


@templates_bp.route('/request_changes')
@check_request
def request_changes():
    # Add your business logic for requesting changes to the event here.
    eventId = request.args.get('eventId')
    who = request.args.get('who')
    token = request.args.get('tokenId')

    return send_changes_request(eventId, who, token)


@templates_bp.route('/notify_reservation', methods=['GET'])
@token_required
def notify_reservation():
    """
    Endpoint para notificar a reitoria sobre uma nova reserva.
    Recebe o ID do evento/reserva e outras informações por JSON.
    """
    event_id = request.args.get('eventId')
    if not event_id:
        return jsonify({'error': 'eventId is required'}), 400

    # Só o organizador do evento pode pedir este aviso.
    event = FlowController.find_event_by_event_id(event_id) if ObjectId.is_valid(event_id) else None
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    owner = ((event.get('organizer') or {}).get('email') or '').strip().lower()
    if owner != (request.headers.get('email') or '').strip().lower():
        return jsonify({'error': 'Only the organizer can notify about this event'}), 403

    try:
        if os.getenv("FLASK_ENV") == "development":
            # No ambiente de desenvolvimento, retorna o conteúdo HTML
            html_content = send_reservation_info_to_reitoria(event_id)
            return html_content
        else:
            # Em produção, envia o email e retorna status
            response = send_reservation_info_to_reitoria(event_id)
            if hasattr(response, 'status_code') and response.status_code == 200:
                return jsonify({'success': True, 'message': 'Email enviado com sucesso para a reitoria'}), 200
            else:
                return jsonify({'success': False, 'message': 'Falha ao enviar email'}), 500
    except Exception as e:
        AppLogger.log(
            Logmessage.NOTIFY_RESERVATION_FAILED, LogType.ERROR,
            event_id=event_id, error=type(e).__name__, ip_address=request.remote_addr)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@templates_bp.route('/store_changes', methods=['POST'])
def store_changes():
    mudancas = request.form.get('mudancas')
    if not mudancas:
        return jsonify({'error': 'Faltou fornecer as mudanças.'}), 400
    else:
        return render_template(
        'email/mudanças_prof.html',
        mensagem=mudancas,
        )
