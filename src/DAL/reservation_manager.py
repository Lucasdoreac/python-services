from typing import Dict, Any

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

    def insert_reservation(self, room_id, event_id, date, start_time, end_time):
        """
        Cria uma reserva para uma sala específica.

        Args:
            room_id (str): Identificador da sala.
            event_id (str): Identificador do evento associado à reserva.
            date (datetime.date): Data da reserva.
            start_time (datetime.time): Horário de início da reserva.
            end_time (datetime.time): Horário de término da reserva.

        Returns:
            dict: O documento de reserva inserido.

        Raises:
            ValueError: Se houver conflito com outro agendamento.
        """
        reservation_start_time = datetime.combine(date, start_time)
        reservation_end_time = datetime.combine(date, end_time)

        # Verifica conflitos na reserva para o mesmo horário
        conflict = self.reservation_collection.find_one({
            "roomId": room_id,
            "startAt": {"$lt": reservation_end_time},
            "endAt": {"$gt": reservation_start_time}
        })
        if conflict:
            raise ValueError("This time slot is already booked.")

        reservation = {
            "roomId": room_id,
            "eventId": event_id,  # Armazena o eventId no documento
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

    def insert_event(self, event_data):
        """
            Insere um novo evento na coleção de eventos do banco de dados.

            Args:
                event_data (dict): Dicionário contendo os dados do evento a ser inserido.

            Returns:
                str: ID do evento inserido convertido para string, útil para serialização.

            Raises:
                Exception: Repassa exceções ocorridas durante a inserção no banco de dados.
            """
        try:
            result = self.events_collection.insert_one(event_data)
            return str(result.inserted_id)

        except Exception as e:
            raise e

    def update_event(self, event_id: str, event_data: Dict[str, Any]):
        """
        Atualiza um evento existente na coleção de eventos.

        Args:
            event_id (str): ID do evento a ser atualizado.
            event_data (dict): Dicionário contendo os dados atualizados do evento.

        Returns:
            str: ID do evento atualizado, útil para confirmação.

        Raises:
            Exception: Repassa exceções ocorridas durante a atualização no banco de dados.
        """
        try:
            from bson import ObjectId
            result = self.events_collection.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": event_data}
            )
            if result.modified_count > 0:
                return event_id
            else:
                # Se nenhum documento foi modificado, pode significar que os dados são idênticos
                return event_id
        except Exception as e:
            raise e
