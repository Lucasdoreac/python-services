from flask import Blueprint, jsonify, request, make_response
from flasgger import swag_from
from .swagger_docs import get_swagger_specification
from BLL import FlowController,pdf
from .auth_decorators import token_required
from SLL.py_log import AppLogger,LogType,Logmessage
from BLL import send_to_coordenacao


# Define your Flask Blueprint
events_bp = Blueprint('events', __name__)


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
            if not user_email:
                AppLogger.log(
                    "Parâmetro userEmail não informado.",
                    LogType.WARNING,
                    ip_address=request.remote_addr,
                )
                return jsonify({'error': 'Parâmetro userEmail é obrigatório'}), 400

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
        if not user_email:
            return jsonify({'error': 'Missing user email in headers'}), 400

        data['userEmail'] = user_email

        result = FlowController.update_event(event_id, data)

        try:
            if data['status'] == 'requested':
                pdf.generate_event_pdf(event_id=data['eventId'])
                send_to_coordenacao(event_id=data['eventId'])
        except Exception as e:
            AppLogger.log(
                f"Erro ao gerar PDF do evento {data['eventId']}: {e}",
                LogType.ERROR,
                ip_address=request.remote_addr,
            )

        response = make_response(result)
        response.headers['Cache-Control'] = 'no-cache, no-store'
        response.headers['Pragma'] = 'no-cache'
        return response
