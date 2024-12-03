from flask import Blueprint, jsonify, request
from flasgger import swag_from
from datetime import date,datetime
from .swagger_docs import get_swagger_specification
from .auth_decorators import api_key_required
from BLL import FlowController
from SLL.py_log import AppLogger,LogType,Logmessage

resources_bp = Blueprint('resources', __name__)


class ResourcesRoutes:

    @staticmethod
    @resources_bp.route('/buildings', methods=['GET'])
    @api_key_required
    @swag_from(get_swagger_specification(path='buildings', method='GET'))
    def get_buildings():
        buildings = FlowController.find_all_buildings()
        if buildings:
            return jsonify({'buildings': buildings}), 200
        AppLogger.log(
            Logmessage.BUILDING_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "Buildings not found"}), 404

    @staticmethod
    @resources_bp.route('/rooms', methods=['GET'])
    @api_key_required
    @swag_from(get_swagger_specification(path='rooms', method='GET'))
    def get_rooms():
        rooms = FlowController.find_all_rooms()
        if rooms:
            return jsonify({'rooms': rooms}), 200
        AppLogger.log(
            Logmessage.ROOMS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "Rooms not found"}), 404


resources_routes = ResourcesRoutes()
