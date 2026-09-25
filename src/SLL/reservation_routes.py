from flask import Blueprint, jsonify, request
from flasgger import swag_from
from .swagger_docs import get_swagger_specification
from .auth_decorators import token_required
from BLL import FlowController
from SLL.py_log import AppLogger,LogType,Logmessage


reservation_bp = Blueprint('reservation_bp', __name__)


class ReservationRoutes:
    @staticmethod
    @reservation_bp.route('/reservations', methods=['POST'])
    @token_required
    @swag_from(get_swagger_specification(path='reservations', method='POST'))
    def post_reservation():
        data = request.json
        if not data:
            AppLogger.log(
                Logmessage.MISSING_DATA,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Missing date'}), 400

        if FlowController.is_reserved(data['reservationDate'], data["roomId"]):
            return jsonify({'error': 'Room already reserved for this time'}), 409
        return FlowController.register_reservation_from_json(data)

    @staticmethod
    @reservation_bp.route('/reservations/<string:date>', methods=['GET'])
    @swag_from(get_swagger_specification(path='reservations', method='GET', resource='date'))
    def get_reservation_by_date(date: str):
        reservation = FlowController.filter_reservation_by_date(date)
        if reservation:
            return jsonify({"reservations": reservation}), 200
        AppLogger.log(
            Logmessage.RESERVATION_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({"error": "Reservation not found"}), 404


    @staticmethod
    @reservation_bp.route('/reservations', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='reservations', method='GET', resource='by-event'))
    def get_reservations_by_event_id():
        event_id = request.args.get('eventId')
        if not event_id:
            AppLogger.log(
            "Parâmetro eventId não informado.",
                    LogType.WARNING,
                    ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Parâmetro eventId é obrigatório'}), 400

        reservations = FlowController.find_reservation_by_event_id(event_id)
        if not reservations:
            AppLogger.log(
                Logmessage.RESERVATION_NOT_FOUND,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': 'Events not found'}), 404

        return  reservations, 200

reservation_routes = ReservationRoutes()
