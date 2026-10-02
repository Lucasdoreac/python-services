from functools import wraps

from bson import ObjectId
from flask import Blueprint, Response, jsonify, request, make_response
from flasgger import swag_from

from utils.enums import EventStatus
from DAL import ReservationConflict, ReservationManager
from .swagger_docs import get_swagger_specification
from BLL import FlowController,pdf
from .auth_decorators import token_required
from . import signed_links
from SLL.py_log import AppLogger,LogType,Logmessage
from BLL import send_to_coordenacao, send_reservation_info_to_reitoria


# Define your Flask Blueprint
events_bp = Blueprint('events', __name__)


def owner_required(function):
    """Permite alteração e submissão somente ao organizador autenticado."""
    @wraps(function)
    def decorated(event_id, *args, **kwargs):
        event = (
            FlowController.find_event_by_event_id(event_id)
            if ObjectId.is_valid(event_id)
            else None
        )
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        owner_email = ((event.get('organizer') or {}).get('email') or '').strip().lower()
        request_email = (request.headers.get('email') or '').strip().lower()
        if owner_email != request_email:
            AppLogger.log(
                Logmessage.EVENT_OWNER_MISMATCH,
                LogType.WARNING,
                event_id=event_id,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Only the organizer can change this event'}), 403
        return function(event_id, *args, **kwargs)
    return decorated


def _status_code(result):
    return result[1] if isinstance(result, tuple) else getattr(result, 'status_code', 200)


def update_and_start_approval(event_id, data):
    if data.get('status') == 'requested':
        if data.get('classificacao') in ['lecture', 'workshop']:
            data['status'] = EventStatus.WAITING.value
            result = FlowController.update_event(event_id, data)
            if _status_code(result) >= 400:
                return result
            try:
                pdf.generate_event_pdf(event_id=data['eventId'])
                send_to_coordenacao(event_id=data['eventId'])
            except Exception as error:
                AppLogger.log(
                    Logmessage.EVENT_APPROVAL_START_FAILED,
                    LogType.ERROR,
                    event_id=data.get('eventId'),
                    error=error,
                    ip_address=request.remote_addr,
                )
            return result
        if data.get('classificacao') in ['class', 'exam']:
            data['status'] = EventStatus.DIRECT_APPROVAL.value
            result = FlowController.update_event(event_id, data)
            if _status_code(result) >= 400:
                return result
            try:
                send_reservation_info_to_reitoria(event_id=data['eventId'])
            except Exception as error:
                AppLogger.log(
                    Logmessage.EVENT_APPROVAL_START_FAILED,
                    LogType.ERROR,
                    event_id=data.get('eventId'),
                    error=error,
                    ip_address=request.remote_addr,
                )
            return result
    return FlowController.update_event(event_id, data)


class EventsRoutes:
    @staticmethod
    @events_bp.route('/events/<string:event_id>/pdf', methods=['GET'])
    def get_event_pdf(event_id):
        """Serve the generated event PDF stored in MongoDB, only for a signed link."""
        if not signed_links.verify(event_id, request.args.get('exp'), request.args.get('sig')):
            return jsonify({'error': 'Forbidden'}), 403
        try:
            pdf_document = ReservationManager().get_pdf_by_event_id(event_id)
            if not pdf_document or not pdf_document.get('content'):
                return jsonify({'error': 'PDF not found'}), 404

            response = Response(
                pdf_document['content'],
                mimetype=pdf_document.get('contentType', 'application/pdf'),
            )
            response.headers['Content-Disposition'] = (
                f"inline; filename=\"{pdf_document.get('filename', f'{event_id}.pdf')}\""
            )
            response.headers['Cache-Control'] = 'private, no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
        except Exception as error:
            AppLogger.log(
                f"Erro ao buscar PDF do evento: {error}",
                LogType.ERROR,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Internal Server Error'}), 500

    @staticmethod
    @events_bp.route('/events', methods=['POST'])
    @token_required
    @swag_from(get_swagger_specification(path='events', method='POST'))
    def post_event():
        """
            Endpoint para criação de um novo evento.

            Obtém os dados JSON do request, extrai o email do usuário a partir dos headers,
            valida a presença de campos essenciais e delega a criação do evento para a função
            create_event.

            Returns:
                Response: Objeto Flask Response contendo o ID do evento criado e o status HTTP 201,
                          ou uma mensagem de erro e o status HTTP correspondente.
        """
        data = request.json
        user_email = request.headers.get('email')
        data['userEmail'] = user_email
        if not data:
            AppLogger.log(
                Logmessage.MISSING_DATA,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Missing data'}), 400
        id_event_response = FlowController.create_event(data)

        # Se id_event_response for uma tupla ou tiver o método get_json, extraia o valor:
        if isinstance(id_event_response, tuple):
            response_obj = id_event_response[0]
        else:
            response_obj = id_event_response

        # Se id_event_response for uma tupla ou tiver o método get_json, extraia o valor:
        id_event = response_obj.get_json().get('eventId') if hasattr(response_obj, 'get_json') else id_event_response

        return  jsonify({'eventId': id_event})

    @staticmethod
    @events_bp.route('/events', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='events', method='GET'))
    def get_events():
        try:
            user_email = request.headers.get('email')

            events = FlowController.find_events_by_user_email(user_email)
            if not events:
                AppLogger.log(
                    Logmessage.EVENTS_NOT_FOUND,
                    LogType.INFO,
                    ip_address=request.remote_addr,
                )
                return jsonify({'error': 'Events not found'}), 404

            return jsonify({'events': events}), 200

        except Exception as error:
            AppLogger.log(
            f"Erro interno: {error}",
            LogType.ERROR,
            ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Internal Server Error'}), 500

    @events_bp.route('/events/<string:event_id>', methods=['PUT'])
    @token_required
    @owner_required
    @swag_from(get_swagger_specification(path='events', method='PUT'))
    def put_event(event_id):
        """
        Endpoint para atualização de um evento existente.

        Obtém os dados JSON do request, extrai o email do usuário a partir dos headers,
        e delega a atualização do evento (identificado por event_id) para a função
        FlowController.update_event.

        Args:
            event_id (str): ID do evento a ser atualizado.

        Returns:
            Response: Objeto Flask Response contendo o ID do evento atualizado e o status HTTP 200,
                      ou uma mensagem de erro e o status HTTP correspondente.
        """
        data = request.get_json()
        if not data:
            AppLogger.log(
                Logmessage.MISSING_DATA,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Missing data'}), 400

        user_email = request.headers.get('email')

        data['userEmail'] = user_email
        result = update_and_start_approval(event_id, data)

        response = make_response(result)
        response.headers['Cache-Control'] = 'no-cache, no-store'
        response.headers['Pragma'] = 'no-cache'
        return response

    @staticmethod
    @events_bp.route('/events/<string:event_id>/submit', methods=['POST'])
    @token_required
    @owner_required
    @swag_from(get_swagger_specification(path='events', method='SUBMIT'))
    def submit_event(event_id):
        """Reserva a sala e envia o evento para aprovação em uma chamada."""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data'}), 400
        try:
            room_id = data['roomId']
            reservation_date = data['reservationDate']
        except KeyError as error:
            return jsonify({'error': f'Missing field: {error}'}), 400

        data.update({
            'eventId': event_id,
            'status': 'requested',
            'userEmail': request.headers.get('email'),
        })
        try:
            reservation = FlowController.reserve_for_event(event_id, room_id, reservation_date)
        except ReservationConflict as error:
            return jsonify({'error': str(error)}), 409
        except ValueError as error:
            return jsonify({'error': f'Invalid data format: {error}'}), 400

        result = update_and_start_approval(event_id, data)
        if _status_code(result) >= 400 and reservation is not None:
            FlowController.undo_reservation(reservation)

        response = make_response(result)
        response.headers['Cache-Control'] = 'no-cache, no-store'
        response.headers['Pragma'] = 'no-cache'
        return response
