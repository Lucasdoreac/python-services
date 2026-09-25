from flask import Blueprint, jsonify, request, make_response
from flasgger import swag_from

from utils.enums import EventStatus
from .swagger_docs import get_swagger_specification
from BLL import FlowController,pdf
from .auth_decorators import token_required
from .ownership import owner_required
from SLL.py_log import AppLogger,LogType,Logmessage
from BLL import send_to_coordenacao, send_reservation_info_to_reitoria
from DAL import ReservationConflict


# Define your Flask Blueprint
events_bp = Blueprint('events', __name__)


def _status(result):
    return result[1] if isinstance(result, tuple) else getattr(result, "status_code", 200)


def update_and_start_approval(event_id, data):
    """Grava o evento e, se veio com status "requested", começa a aprovação
    (PDF + e-mail para a Coordenação, ou aviso direto para a Reitoria).
    Usado pelo PUT /events/<id> e pelo POST /events/<id>/submit."""
    result = FlowController.update_event(event_id, data)
    if _status(result) >= 400:
        return result  # nada gravado: não começa aprovação (nem PDF/e-mail)
    try:
        if data['status'] == 'requested': # flag que o front-end envia quando o evento é solicitado
            # Enviar informação sobre evento ou reserva simples
            if data['classificacao'] in ['lecture', 'workshop']:
                data['status'] = EventStatus.WAITING.value
                pdf.generate_event_pdf(event_id=data['eventId'])
                send_to_coordenacao(event_id=data['eventId'])
            elif data['classificacao'] in ['class', 'exam']:
                data['status'] = EventStatus.DIRECT_APPROVAL.value
                FlowController.update_event(event_id, data)
                send_reservation_info_to_reitoria(event_id=data['eventId'])
            result = FlowController.update_event(event_id, data)
    except Exception as e:
        # Antes o "e" era capturado e nunca usado: qualquer erro nesse
        # bloco (ex.: PDF, email) ficava sem nenhum rastro no log, e a
        # resposta seguia 200 com o "result" desatualizado (status antigo).
        AppLogger.log(
            f"Erro ao começar processo de aprovação (status = requested) {data['eventId']}: {e}",
            LogType.ERROR,
            ip_address=request.remote_addr,
        )
    return result


class EventsRoutes:
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

        data['userEmail'] = request.headers.get('email')
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
        """
        Envia o evento para aprovação reservando a sala na mesma requisição (issue #64).

        Substitui o par POST /reservations + PUT /events/<id> do front: se o
        evento não gravar, a reserva criada aqui é desfeita (sala não fica presa)
        e uma nova tentativa reaproveita a reserva do próprio evento em vez de 409.
        """
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data'}), 400
        try:
            room_id, reservation_date = data['roomId'], data['reservationDate']
        except KeyError as e:
            return jsonify({'error': f'Missing field: {e}'}), 400

        data['eventId'] = event_id
        data['status'] = 'requested'
        data['userEmail'] = request.headers.get('email')
        try:
            reservation = FlowController.reserve_for_event(event_id, room_id, reservation_date)
        except ReservationConflict as e:
            return jsonify({'error': str(e)}), 409
        except ValueError as e:
            return jsonify({'error': f'Invalid data format: {e}'}), 400

        result = update_and_start_approval(event_id, data)
        if _status(result) >= 400 and reservation is not None:
            FlowController.undo_reservation(reservation)

        response = make_response(result)
        response.headers['Cache-Control'] = 'no-cache, no-store'
        response.headers['Pragma'] = 'no-cache'
        return response
