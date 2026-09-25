import os
from flask import Blueprint, request, jsonify, render_template
from flasgger import swag_from
from SLL.swagger_docs import get_swagger_specification
from BLL import send_to_reitoria, send_to_coordenacao, send_event_status, send_reservation_info_to_reitoria
from BLL.send_emails import verify_token_from_email, request_event_changes, token_step
from utils.enums import EmailStep
from functools import wraps
from settings import get_email_settings

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
@swag_from(get_swagger_specification('approval', 'ADMIN'))
@check_request
def administration_approval():
    eventId = request.args.get('eventId')
    step = request.args.get('step')

    if not step:
        return "Not found", 404
    step = int(step)
    if step == 0:
        if get_email_settings().email_dry_run:
            return send_to_coordenacao(eventId)
    elif step == 1:
        if get_email_settings().email_dry_run:
            return send_to_reitoria(eventId)


@templates_bp.route('/approve')
@swag_from(get_swagger_specification('approval', 'APPROVE'))
@check_request
def approve():
    eventId = request.args.get('eventId')
    who = request.args.get('who')
    token = request.args.get('tokenId')

    send_event_status(eventId, True, who, token)
    if who == "coordenacao":
        if get_email_settings().email_dry_run:
            return send_to_reitoria(eventId)
        send_to_reitoria(eventId)
    return "Evento aprovado!"


@templates_bp.route('/reject')
@swag_from(get_swagger_specification('approval', 'REJECT'))
@check_request
def reject():
    eventId = request.args.get('eventId')
    who = request.args.get('who')
    token = request.args.get('tokenId')

    if get_email_settings().email_dry_run:
        return send_event_status(eventId, False, who, token)
    send_event_status(eventId, False, who, token)
    return "Evento rejeitado!"


@templates_bp.route('/request_changes', methods=['GET', 'POST'])
# Um arquivo por método: com dicionário o flasgger ignora `methods`.
@swag_from('swagger_specs/request_changes_get.yml', methods=['GET'])
@swag_from('swagger_specs/request_changes_post.yml', methods=['POST'])
@check_request
def request_changes():
    """
    Link "Solicitar alterações" do e-mail da Coordenação (issue #35).
    GET abre o formulário; POST grava o pedido e avisa a pessoa solicitante.
    Só a Coordenação pede mudança: token de outra etapa dá 403.
    """
    eventId = request.args.get('eventId')
    token = request.args.get('tokenId')
    if token_step(token) != EmailStep.COORDENACAO.value:
        return "Só a Coordenação pode pedir mudanças.", 403

    if request.method == 'GET':
        return render_template('email/pedir_mudancas.html', eventId=eventId, tokenId=token)

    message = (request.form.get('mudancas') or '').strip()
    if not message:
        return render_template('email/pedir_mudancas.html', eventId=eventId, tokenId=token,
                               erro='Descreva as mudanças.'), 400
    sent = request_event_changes(eventId, message, token)
    if get_email_settings().email_dry_run:
        return sent
    return "Pedido de mudança enviado à pessoa solicitante."


@templates_bp.route('/notify_reservation', methods=['GET'])
@swag_from(get_swagger_specification('approval', 'NOTIFY'))
def notify_reservation():
    """
    Endpoint para notificar a reitoria sobre uma nova reserva.
    Recebe o ID do evento/reserva e outras informações por JSON.
    """
    event_id = request.args.get('eventId')
    if not event_id:
        return jsonify({'error': 'eventId is required'}), 400


    if not event_id:
        return jsonify({'error': 'eventId é obrigatório'}), 400

    try:
        if get_email_settings().email_dry_run:
            # Em dry-run (EMAIL_DRY_RUN), retorna o conteúdo HTML
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
        return jsonify({'error': str(e)}), 500