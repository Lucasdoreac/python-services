import os
from flask import Blueprint, request, jsonify
from BLL import send_to_reitoria, send_to_coordenacao, send_event_status
from BLL.send_emails import verify_token_from_email, apply_token_action
from functools import wraps
# Create a blueprint for handling templates and related routes.
templates_bp = Blueprint('templates_bp', __name__, template_folder='../templates')

def check_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tokenId = request.args.get('tokenId')
        eventId = request.args.get('eventId')

        if not (eventId and tokenId):
            return "Not found", 404

        is_token_valid = verify_token_from_email(tokenId)

        if is_token_valid is False:
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

    send_event_status(eventId, True, who,token)
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

    if os.getenv("FLASK_ENV") == "development":
        return send_event_status(eventId, False, who, token)
    send_event_status(eventId, False, who, token)
    return "Evento rejeitado!"

@templates_bp.route('/request_changes')
@check_request
def request_changes():
    # Add your business logic for requesting changes to the event here.
    eventId = request.args.get('eventId')
    who = request.args.get('who')
    token = request.args.get('tokenId')

    if who == 'coordenacao':
        apply_token_action(0, "Request Changes", eventId, token)
    else:
        apply_token_action(1, "Request Changes", eventId, token)
    return "Solicitando alterações no evento!"

