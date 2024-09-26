from flask import Blueprint, jsonify, request
from flasgger import swag_from


from BLL import FlowController


reservation_bp = Blueprint('reservation_bp', __name__)


class ReservationRoutes:
    @staticmethod
    @reservation_bp.route('/reservations', methods=['POST'])
    # @swag_from('../open_api/post_reservation.yaml')
    def post_reservation():
        data = request.json
        if not data:
            return jsonify({'error': 'Missing date'}), 400
        return FlowController.register_reservation_from_json(data)

    @staticmethod
    @reservation_bp.route('/reservations/<string:date>', methods=['GET'])
    # @swag_from('../open_api/get_reservation.yaml')
    def get_reservation_by_date(date: str):
        reservations = FlowController.filter_reservation_by_date(date)
        return jsonify(reservations), 200


reservation_routes = ReservationRoutes()
