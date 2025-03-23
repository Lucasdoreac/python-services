import os
from typing import Any, Dict

import requests
from flask import request, jsonify
from datetime import datetime, timedelta
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

    @staticmethod
    def find_events_by_user_email(email):
        return events_repository.find_all({"organizer.email": email })

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

            # Converting the data strings to datetime objects
            date = datetime.strptime(date_str, '%Y-%m-%d')
            start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()

            # Combine date and start_time to form a datetime for the reservation start
            reservation_start = datetime.combine(date, start_time)
            # Add two hours to create the reservation end datetime
            reservation_end = reservation_start + timedelta(hours=2)
            # Extract the time component for end_time
            end_time = reservation_end.time()

            # Creating the object from MongoDB connection
            reservation_system = ReservationManager()

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

    def filter_available_rooms(self, date_str: str, time_str: str, page: int, page_size: int):
        """
        Recebe uma data e um horário e retorna uma lista de salas disponíveis,
        removendo da lista de todas as salas aquelas com reservas que abrangem o horário informado.
        Retorna os campos "id", "name" e "campus" de cada sala disponível.
        """
        # Obter os 'IDs' das salas indisponíveis para o horário informado
        reservation_system = ReservationManager()
        unavailable_room_ids = reservation_system.find_unavailable_room_ids_by_date(date_str, time_str)

        # Buscar todas as salas cadastradas no shared-resources, paginadas
        all_rooms, pagination_config = self.find_all_rooms(page, page_size)

        # Filtrar as salas disponíveis: remover as que estão na lista de indisponíveis
        available_rooms = [
            {
                "id": room.get("id"),
                "name": room.get("name"),
                "campus": room.get("campus")
            }
            for room in all_rooms
            if room.get("id") not in unavailable_room_ids
        ]

        return available_rooms, pagination_config

    def find_all_rooms(self, page: int, page_size: int):
        """
        Busca todas as salas cadastradas no shared-resources, utilizando paginação.
        """
        url = f"{os.getenv('URL_restapi')}/rooms"
        response = requests.get(url, params={"page": page, "page_size": page_size})
        if response.status_code != 200:
            raise Exception("Erro ao buscar salas do shared-resources")

        rooms_json = response.json()
        # Se a resposta possuir paginação, os dados estarão no campo "data"
        all_rooms = rooms_json.get("data", rooms_json)
        pagination_config = rooms_json.get("pagination", {})
        return all_rooms, pagination_config

    def register_event_from_json(data: Dict[str, Any]):

        try:

            name = data["tituloEvento"]
            teacherEmail = data["nomeProfessor"]
            teacherPhone = data["telefone"] if data["telefone"] else ""
            teacherName = teacherEmail.split("@")[0]
            organizer = {"name": teacherName, "email": teacherEmail, "phone": teacherPhone}

            eventTypeId = data["classificacao"]
            odsId = data["odsId"]
            odsName = data["odsName"]
            subscriptionLink = ""
            description = data["descricaoEvento"]
            graduationId = data["courseId"]
            graduationName = data["courseName"]
            targetPublic = data["publicoAlvo"]
            resources = data["recursosNecessarios"] if data["recursosNecessarios"] else ""
            expectedSubscribers = data["numeroParticipantes"]
            roomType = data["espacos"]
            entrepreneuralPath = data.get("trilhaDesc", "")
            extensionProject = data.get("projetoDesc", "")
            studentsMonitors = data.get("alunosMonitores", "")
            eventLogo = ""

            register_system = ReservationManager()
            register_system.insert_event(name, organizer, eventTypeId, odsId, subscriptionLink, description,
                                         graduationId, targetPublic, resources, expectedSubscribers, roomType,
                                         entrepreneuralPath, extensionProject, studentsMonitors, eventLogo)

            return jsonify({'success': "Event registration successful"}), 201

        except KeyError as e:
            return jsonify({'error': f'Missing field: {str(e)}'}), 400
