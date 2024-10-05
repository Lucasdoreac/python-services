from typing import Any, Dict

from flask import request, jsonify
from datetime import datetime
from DAL import *
from DAL.collections_repositories import EventsRepository

# Initialize repository instances
university_repository = UniversityRepository()
buildings_repository = BuildingsRepository()
rooms_repository = RoomsRepository()
types_repository = TypesRepository()
reservations_repository = ReservationsRepository()
events_repository = EventsRepository()


class FlowController:

    @staticmethod
    def find_all_buildings():
        return buildings_repository.find_all()

    @staticmethod
    def find_all_rooms():
        return rooms_repository.find_all()

    @staticmethod
    def find_all_types():
        return types_repository.find_all()

    @staticmethod
    def find_all_events():
        return events_repository.find_all()

    def find_type_by_collection(collection: str):
        type_data = types_repository.get_type_by_collection(collection)
        if type_data:
            return jsonify(type_data), 200
        else:
            return jsonify({'error': 'There is no such type'}), 404

    def register_reservation_from_json(data: Dict[str, Any]):
        try:
            # Extracting fields from data
            room_id = data['room_id']
            course_id = data['course_id']
            date_str = data['date']
            start_time_str = data['start_time']
            end_time_str = data['end_time']

            # Converting the data strings to datetime objects
            date = datetime.strptime(date_str, '%Y-%m-%d')
            start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
            end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()

            # Creating the object from MongoDB connection
            reservation_system = ReservationManager()

            # Calling the insert_reservation method
            reservation_system.insert_reservation(room_id, course_id, date, start_time, end_time)

            return jsonify({'success': "Reservation attempted"}), 201

        except KeyError as e:
            return jsonify({'error': f'Missing field: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid data format: {str(e)}'}), 400

    def filter_reservation_by_date(date: str):

        try:
            # Extracting date
            date_str = date

            # Converting date to datetime object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            filter_by_date = reservations_repository.get_reservation_by_date(date_obj)

            return filter_by_date

        except KeyError as e:
            return jsonify({'error': f'Missing field: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid data format: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f"An error ocucred: {str(e)}"}), 400

    def register_event_from_json(data: Dict[str, Any]):

        try:
            name = data["name"]
            organizer = data["organizer"]
            eventTypeId = data["eventTypeId"]
            odsTypeId = data["odsTypeId"]
            subscriptionLink = data["subscriptionLink"]
            description = data["description"]
            graduationId = data["graduationId"]
            targetPublic = data["targetPublic"]
            resources = data["resources"]
            expectedSubscribers = data["expectedSubscribers"]
            roomType = ["roomType"]
            entrepreneuralPath = data["entrepreneuralPath"]
            extensionProject = data["extensionProject"]
            studentsMonitors = data["studentsMonitors"]
            eventLogo = data["eventLogo"]

            register_system = ReservationManager()
            register_system.insert_event(name, organizer, eventTypeId, odsTypeId, subscriptionLink, description,
                                         graduationId, targetPublic, resources, expectedSubscribers, roomType,
                                         entrepreneuralPath, extensionProject, studentsMonitors, eventLogo)

            return jsonify({'success': "Event registration successful"}), 201

        except KeyError as e:
            return jsonify({'error': f'Missing field: {str(e)}'}), 400
