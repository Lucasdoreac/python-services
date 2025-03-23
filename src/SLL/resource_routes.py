import requests
from flask import Blueprint, jsonify, request
from flasgger import swag_from
import os

from BLL import FlowController
from .auth_decorators import token_required
from .swagger_docs import get_swagger_specification
from SLL.py_log import AppLogger,LogType,Logmessage

resources_bp = Blueprint('resources', __name__)



class ResourcesRoutes:


    @staticmethod
    @resources_bp.route('/rooms/all-rooms', methods=['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='rooms/all-rooms', method='GET'))
    def get_rooms():
        query= """query{
                  rooms{
                    name
                     campus{
                      name
                      id
                    }
                  }
                }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        rooms = data.get("data", {}).get("rooms", [])

        if rooms:
            return jsonify({'rooms': rooms}), 200
        AppLogger.log(
            Logmessage.ROOMS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "Rooms not found"}), 404

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
    @resources_bp.route('/campus',methods = ['GET'])
    @token_required
    @swag_from(get_swagger_specification(path='campus',method='GET'))
    def get_campus():

        search = request.headers.get('search')

        if search:
            query = f"""
            query(search: "{search}") {{
                campus {{
                    id
                    name
                }}
            }}
            """
        else:
            query = """
            query {
                campus {
                    id
                    name
                }
            }
            """

        response = requests.post(f"{os.getenv('URL_graph')}", json = {"query":query})
        data = response.json()
        campus = data.get("data",{}).get("campus",[])

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

        search = request.headers.get('search')
        if search:
            query = f"""
            query(search: "{search}") {{
                disciplines {{
                    name
                }}
            }}
            """
        else:
            query = """query{
                       disciplines {
                         name
                       }
                       }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        disciplines = data.get("data", {}).get("disciplines", [])

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

        search = request.headers.get('search')
        if search:
            query = f"""
            query(search: "{search}") {{
                periods {{
                    name
                }}
            }}
            """
        else:
            query = """query{
                       periods {
                         name
                       }
                       }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        periods = data.get("data", {}).get("periods", [])

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

        search = request.headers.get('search')
        if search:
            query = f"""
            query(search: "{search}") {{
                teachers {{
                    name
                }}
            }}
            """
        else:
            query = """query{
                       teachers {
                         name
                       }
                       }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        teachers = data.get("data", {}).get("teachers", [])

        if teachers:
            return jsonify({'periods': teachers}), 200
        AppLogger.log(
            Logmessage.TEACHERS_NOT_FOUND,
            LogType.INFO,
            ip_address=request.remote_addr,
        )
        return jsonify({'error': "teachers not found"}), 404



resources_routes = ResourcesRoutes()
