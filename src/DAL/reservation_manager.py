from .mongodb_factory import MongoDBConnectionFactory
from datetime import datetime
from bson import ObjectId


class ReservationManager:

    def __init__(self):
        self.db = MongoDBConnectionFactory.get_db()
        self.reservation_collection = self.db.reservations
        self.rooms_collection = self.db.rooms
        self.buildings_collection = self.db.buildings
        self.events_collection = self.db.events

    def insert_reservation(self, room_id, course_id, date, start_time, end_time):
        """
        Creates a reservation for a given room.

        Args:
            room_id: Identifier for the room.
            course_id: Identifier for the course.
            date (datetime.date): The date of the reservation.
            start_time (datetime.time): Start time of the reservation.
            end_time (datetime.time): End time of the reservation.

        Returns:
            dict: The reservation object that was inserted.

        Raises:
            ValueError: if the time slot is already booked.
        """

        reservation_start_time = datetime.combine(date, start_time)
        reservation_end_time = datetime.combine(date, end_time)

        # Check for conflicting reservations
        conflict = self.reservation_collection.find_one({
            "roomId": room_id,
            "startAt": {"$lt": reservation_end_time},
            "endAt": {"$gt": reservation_start_time}
        })
        if conflict:
            raise ValueError("This time slot is already booked.")

        reservation = {
            "roomId": room_id,
            "courseId": course_id,
            "startAt": reservation_start_time,
            "endAt": reservation_end_time,
            "status": "requested"
        }

        self.reservation_collection.insert_one(reservation)
        return reservation

    def find_unavailable_room_ids_by_date(self, date_str: str, time_str: str):
        """
        Recebe uma data no formato 'YYYY-MM-DD' e um horário no formato 'HH:MM:SS'
        e retorna todos os roomId que possuem uma reserva que englobe esse momento.
        """
        try:
            # Converte a data e o horário para objetos datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
            reservation_datetime = datetime.combine(date_obj, time_obj)

            # Consulta: busca reservas onde o momento informado esteja entre startAt e endAt
            query = {
                "startAt": {"$lte": reservation_datetime},
                "endAt": {"$gte": reservation_datetime}
            }
            # Projeção para retornar apenas o campo "roomId"
            projection = {"roomId": 1, "_id": 0}

            results = self.reservation_collection.find(query, projection)
            room_ids = [doc["roomId"] for doc in results]
            return room_ids
        except Exception as e:
            print(f"Erro na busca: {e}")
            return []

    def insert_event(self, name, organizer, eventTypeId, odsTypeId, subscriptionLink, description, graduationId,
                     targetPublic, resources, expectedSubscribers, roomType, entrepreneuralPath, extensionProject, studentsMonitors, eventLogo):

        event = {
            "name": name,
            "status": "análise",
            "organizer": organizer,
            "eventTypeId": eventTypeId,
            "odsTypeId": odsTypeId,
            "subscriptionLink": subscriptionLink,
            "description": description,
            "graduationId": graduationId,
            "targetPublic": targetPublic,
            "resources": resources,
            "expectedSubscribers": expectedSubscribers,
            "roomType": roomType,
            "entrepreneuralPath": entrepreneuralPath,
            "extensionProject": extensionProject,
            "studentsMonitors": studentsMonitors,
            "eventLogo": eventLogo
        }

        self.events_collection.insert_one(event)
