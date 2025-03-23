from flask import Blueprint, jsonify, request
from flasgger import swag_from
from .swagger_docs import get_swagger_specification
from BLL import FlowController
from .auth_decorators import token_required
from SLL.py_log import AppLogger,LogType,Logmessage

# Define your Flask Blueprint
events_bp = Blueprint('events', __name__)


class EventsRoutes:
    @staticmethod
    @events_bp.route('/events', methods=['POST'])
    @token_required
    @swag_from(get_swagger_specification(path='events', method='POST'))
    def post_event():
        # Getting the json data from the request
        data = request.json
        if not data:
            AppLogger.log(
                Logmessage.MISSING_DATA,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Missing data'}), 400
        return FlowController.register_event_from_json(data)

    @staticmethod
    @events_bp.route('/events', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='events', method='GET'))
    def get_events():
        try:
            user_email = request.args.get('userEmail')
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

