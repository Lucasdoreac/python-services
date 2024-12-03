from flask import Blueprint, jsonify, request
from flasgger import swag_from
from datetime import date,datetime
from .swagger_docs import get_swagger_specification
from BLL import FlowController
from .auth_decorators import api_key_required
from SLL.py_log import AppLogger,LogType,Logmessage

# Define your Flask Blueprint
events_bp = Blueprint('events', __name__)


class EventsRoutes:
    @staticmethod
    @events_bp.route('/events', methods=['POST'])
    @api_key_required
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
    @api_key_required
    @swag_from(get_swagger_specification(path='events', method='GET'))
    def get_events():
        events = FlowController.find_all_events()
        if events:
            return jsonify({'events': events}), 200
        AppLogger.log(
            Logmessage.EVENTS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': 'Events not found'}), 404
