import requests
from flask import Blueprint, jsonify, request
from flasgger import swag_from
import os

from BLL import FlowController
from .auth_decorators import token_required
from .swagger_docs import get_swagger_specification
from SLL.py_log import AppLogger,LogType,Logmessage
from sr_requests_module.request_methods import GraphQlRequestMethods

resources_bp = Blueprint('resources', __name__)



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

        if not date_str or not time_str:
            return jsonify({"error": "Parâmetros 'date' e 'time' são obrigatórios."}), 400

        try:
            available_rooms, pagination_config = FlowController().filter_available_rooms(date_str, time_str, page, page_size)
            return jsonify({"data": available_rooms, "pagination": pagination_config}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @resources_bp.route('/rooms', methods=['GET'])
    @token_required
    def get_rooms_by_id():
        try:
            room_id = request.args.get("collection")
            room_obj = FlowController.find_room_by_id(room_id)
            return room_obj, 200
        except Exception as e:
            return jsonify({"error": str(e)})



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

            response = requests.get(url)
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
            return jsonify({'error': 'Failed to fetch data from external API.', 'details': str(e)}), 502
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
