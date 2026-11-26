import logging
import re
from datetime import datetime, timedelta, timezone
import requests
from flask import Blueprint, jsonify, request
from flasgger import swag_from
import os
from BLL import FlowController
from .auth_decorators import token_required
from .swagger_docs import get_swagger_specification
from SLL.py_log import AppLogger,LogType,Logmessage
from .cluster_api.request_methods import GraphQlRequestMethods, catalog_headers

resources_bp = Blueprint('resources', __name__)


def parse_availability_start(value):
    """ISO explícito em UTC ingênuo, representação usada no Mongo."""
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})', value):
        raise ValueError('invalid start_at')
    if not value.endswith('Z') and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError('invalid offset')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    utc = instant.astimezone(timezone.utc).replace(tzinfo=None)
    utc + timedelta(hours=3)
    return utc



class ResourcesRoutes:


    @staticmethod
    @resources_bp.route('/rooms/all-rooms', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='rooms/all-rooms', method='GET'))
    def get_rooms():

        rooms = GraphQlRequestMethods.get_all_rooms_request()

        if rooms:
            return jsonify({'rooms': rooms}), 200
        AppLogger.log(
            Logmessage.ROOMS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "Rooms not found"}), 404

    @staticmethod
    @resources_bp.route('/rooms/search-rooms', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='rooms/search-rooms', method='GET'))
    def get_all_rooms():

        rooms = GraphQlRequestMethods.get_specific_room()

        if rooms:
            return jsonify({'rooms': rooms}), 200
        AppLogger.log(
            Logmessage.ROOMS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "Room not found by search method"}), 404

    @staticmethod
    @resources_bp.route('/rooms/available-rooms', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='rooms/available-rooms', method='GET'))
    def get_available_rooms():
        # Obtém os parâmetros da query string
        date_str = request.args.get("date")
        time_str = request.args.get("time")
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)
        room_name = request.args.get("room_name", "")

        start_values = request.args.getlist("start_at")
        if start_values:
            if len(start_values) != 1 or 'date' in request.args or 'time' in request.args:
                return jsonify({"error": "Use start_at uma vez, sem date ou time."}), 400
            try:
                start_at = parse_availability_start(start_values[0])
            except (ValueError, OverflowError):
                return jsonify({"error": "start_at deve ser ISO 8601 com fuso explícito."}), 400
        elif not date_str or not time_str:
            return jsonify({"error": "Parâmetros 'date' e 'time' são obrigatórios."}), 400
        else:
            start_at = None
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                datetime.strptime(time_str, "%H:%M:%S")
            except ValueError:
                return jsonify({"error": "Data ou horário inválido."}), 400

        try:
            if start_at is None:
                available_rooms, pagination_config = FlowController().filter_available_rooms(date_str, time_str, page, page_size, room_name)
            else:
                available_rooms, pagination_config = FlowController().filter_available_rooms(date_str, time_str, page, page_size, room_name, start_at=start_at)
            return jsonify({"data": available_rooms, "pagination": pagination_config}), 200
        except Exception as e:
            AppLogger.log(
                message=Logmessage.INTERNAL_APIS_CRASHED,
                log_type=LogType.ERROR,
                ip_address=request.remote_addr,
                payload=f"body_length={len(request.data or b'')}",
                endpoint=request.path,
                error=type(e).__name__,
            )
            return jsonify({"error": "Impossível fazer essa pesquisa de sala"}), 500

    @staticmethod
    @resources_bp.route('/rooms', methods=['GET'])
    @token_required
    def get_rooms_by_id():
        room_id = request.args.get("roomId")
        if not room_id:
            return jsonify({"error": "roomId is required"}), 400
        try:
            result = FlowController.find_room_by_id(room_id)
        except Exception:
            return jsonify({"error": "An unexpected error occurred"}), 500
        if isinstance(result, tuple):  # resposta de erro devolvida pela consulta
            return result
        return jsonify(result), 200



    @staticmethod
    @resources_bp.route('/campus',methods = ['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='campus',method='GET'))
    def get_campus():

        campus = GraphQlRequestMethods.get_all_campus_request()

        if campus:
            return jsonify({'campus':campus}),200
        AppLogger.log(
            Logmessage.CAMPUS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "Campus not found"}), 404


    @staticmethod
    @resources_bp.route('/courses',methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='courses',method='GET'))
    def get_courses():
        try:

            course_name = request.args.get('course_name')
            url = f"{os.getenv('URL_restapi')}/courses/"

            if course_name:
                url += f"?course_name={course_name}"

            response = requests.get(url, headers=catalog_headers())
            response.raise_for_status()

            data = response.json()
            courses = data.get("data", [])

            if courses:
                return jsonify({'courses':courses}),200
            AppLogger.log(
                Logmessage.COURSES_NOT_FOUND,
                LogType.INFO,
                ip_address=request.remote_addr,
            )
            return jsonify({'error': "Course not found"}), 404

        except requests.exceptions.RequestException as e:
            # Handle errors in the external API call
            logging.getLogger(__name__).warning('Catalog request failed: %s', type(e).__name__)
            return jsonify({'error': 'Failed to fetch data from external API.'}), 502
        except ValueError:
            # Handle invalid JSON responses
            return jsonify({'error': 'Invalid JSON response from external API.'}), 500


    @staticmethod
    @resources_bp.route('/disciplines', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='disciplines', method='GET'))
    def get_disciplines():

        disciplines = GraphQlRequestMethods.get_disciplines_request()

        if disciplines:
            return jsonify({'disciplines': disciplines}), 200
        AppLogger.log(
            Logmessage.DISCIPLINES_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "disciplines not found"}), 404


    @staticmethod
    @resources_bp.route('/periods', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='periods', method='GET'))
    def get_periods():

        periods = GraphQlRequestMethods.get_all_periods_request()
        if periods:
            return jsonify({'periods': periods}), 200
        AppLogger.log(
            Logmessage.PERIODS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "periods not found"}), 404


    @staticmethod
    @resources_bp.route('/teachers', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='teachers', method='GET'))
    def get_teachers():

        teachers = GraphQlRequestMethods.get_teachers_request()

        if teachers:
            return jsonify({'teachers': teachers}), 200
        AppLogger.log(
            Logmessage.TEACHERS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "teachers not found"}), 404



resources_routes = ResourcesRoutes()
