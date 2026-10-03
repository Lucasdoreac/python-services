import os
from flask import Blueprint, request, jsonify, render_template, make_response
from bson import ObjectId
from BLL import send_to_reitoria, send_to_coordenacao, send_reservation_info_to_reitoria
from SLL.auth_decorators import token_required
from BLL.index import FlowController
from BLL.send_emails import verify_token_from_email, perform_approval_action, MAX_CHANGE_MESSAGE

# Create a blueprint for handling templates and related routes.
templates_bp = Blueprint('templates_bp', __name__, template_folder='../templates')


def _approval_action(action):
    def secure(response):
        response = make_response(response)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    event_id = request.values.get("eventId")
    token_id = request.values.get("tokenId")
    if not event_id or not token_id:
        return secure((jsonify({'error': 'Link de aprovação inválido'}), 404))

    token = verify_token_from_email(token_id, event_id, action)
    if not token:
        return secure((jsonify({'error': 'Link expirado ou inválido'}), 404))

    step = int(token["step"])
    who = "Coordenação" if step == 0 else "Reitoria"
    labels = {
        "approve": "aprovar este evento",
        "reject": "rejeitar este evento",
        "request_changes": "solicitar alterações neste evento",
    }

    def confirmation(status=200, message=None, error=None):
        return secure((render_template(
            "email/confirmar_acao.html",
            event_id=event_id,
            token_id=token_id,
            action=action,
            action_label=labels[action],
            who=who,
            message=message,
            error=error,
        ), status))

    if request.method == "GET":
        return confirmation()

    message = None
    if action == "request_changes":
        message = (request.form.get("message") or "").strip()
        if not 1 <= len(message) <= MAX_CHANGE_MESSAGE:
            # refused before the token is consumed: the coordinator can fix the text and send again
            return confirmation(400, message, f"Descreva as alterações (até {MAX_CHANGE_MESSAGE} caracteres).")

    result = perform_approval_action(event_id, token_id, action, message=message)
    if not result:
        return secure((jsonify({'error': 'A etapa do evento mudou ou o link já foi utilizado'}), 409))
    return secure({
        "approve": "Evento aprovado!",
        "reject": "Evento rejeitado!",
        "request_changes": "Solicitação de alterações registrada.",
    }[action])


@templates_bp.route('/administration_approval', methods=['GET', 'POST'])
def administration_approval():
    eventId = request.args.get('eventId')
    token_id = request.args.get('tokenId')
    token = verify_token_from_email(token_id, eventId, "approve") if token_id and eventId else None
    if not token:
        return "Not found", 404
    step = int(token["step"])
    if step == 0:
        if os.getenv("FLASK_ENV") == "development":
            return send_to_coordenacao(eventId)
    elif step == 1:
        if os.getenv("FLASK_ENV") == "development":
            return send_to_reitoria(eventId)


@templates_bp.route('/approve', methods=['GET', 'POST'])
def approve():
    return _approval_action("approve")


@templates_bp.route('/reject', methods=['GET', 'POST'])
def reject():
    return _approval_action("reject")


@templates_bp.route('/request_changes', methods=['GET', 'POST'])
def request_changes():
    return _approval_action("request_changes")


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

    event = FlowController.find_event_by_event_id(event_id) if ObjectId.is_valid(event_id) else None
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    owner = ((event.get('organizer') or {}).get('email') or '').strip().lower()
    if owner != (request.headers.get('email') or '').strip().lower():
        return jsonify({'error': 'Only the organizer can notify about this event'}), 403

    if not event_id:
        return jsonify({'error': 'eventId é obrigatório'}), 400

    try:
        if os.getenv("FLASK_ENV") == "development":
            # No ambiente de desenvolvimento, retorna o conteúdo HTML
            html_content = send_reservation_info_to_reitoria(event_id)
            return html_content
        else:
            # Em produção, envia o email e retorna status
            response = send_reservation_info_to_reitoria(event_id)
            if hasattr(response, 'status_code') and response.status_code == 202:
                return jsonify({
                    'success': True,
                    'sent': False,
                    'message': 'Email dry-run; mensagem não enviada'
                }), 202
            if hasattr(response, 'status_code') and response.status_code == 200:
                return jsonify({'success': True, 'message': 'Email enviado com sucesso para a reitoria'}), 200
            else:
                return jsonify({'success': False, 'message': 'Falha ao enviar email'}), 500
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred'}), 500
