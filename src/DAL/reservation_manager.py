from typing import Dict, Any
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError

from SLL import AppLogger, LogType, Logmessage
from .mongodb_factory import MongoDBConnectionFactory
from utils.enums import EventStatus


ACTIVE_RESERVATION_STATUSES = [
    "requested",
    EventStatus.DRAFT.value,
    EventStatus.WAITING.value,
    EventStatus.APPROVED_BY_COORDENACAO.value,
    EventStatus.APPROVED_BY_REITORIA.value,
    EventStatus.REQUESTED_CHANGE.value,
    EventStatus.DIRECT_APPROVAL.value,
]


class ReservationConflict(ValueError):
    """A sala já está reservada no horário solicitado."""


class ReservationManager:

    @staticmethod
    def ensure_indexes():
        """Create the partial unique index used to reject duplicate reservations.

        The overlap check in ``insert_reservation`` is not atomic across
        concurrent requests. This index preserves the Production guard for
        active reservations with the same room and start time.
        """
        MongoDBConnectionFactory.get_db().reservations.create_index(
            [("roomId", 1), ("startAt", 1)],
            name="uniq_active_reservation_room_start",
            unique=True,
            partialFilterExpression={"status": {"$in": ACTIVE_RESERVATION_STATUSES}},
        )

    def __init__(self):
        self.db = MongoDBConnectionFactory.get_db()
        self.reservation_collection = self.db.reservations
        self.rooms_collection = self.db.rooms
        self.buildings_collection = self.db.buildings
        self.events_collection = self.db.events
        self.pdfs_collection = self.db.pdfs
        self.send_email_collection = self.db.send_email

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
            "endAt": {"$gt": reservation_start_time},
            "status": {"$in": ACTIVE_RESERVATION_STATUSES},
        })
        if conflict:
            raise ReservationConflict("This time slot is already booked.")

        reservation = {
            "roomId": room_id,
            "eventId": event_id,  # Armazena o eventId no documento
            "startAt": reservation_start_time,
            "endAt": reservation_end_time,
            "status": EventStatus.WAITING.value,
        }

        try:
            self.reservation_collection.insert_one(reservation)
        except DuplicateKeyError as error:
            raise ReservationConflict("This time slot is already booked.") from error
        return reservation

    def find_active_reservation(self, event_id, room_id, start_at):
        return self.reservation_collection.find_one({
            "eventId": event_id,
            "roomId": room_id,
            "startAt": start_at,
            "status": {"$in": ACTIVE_RESERVATION_STATUSES},
        })

    def delete_reservation(self, reservation_id):
        self.reservation_collection.delete_one({"_id": reservation_id})

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
            # e que não tenham sido rejeitadas pela reitoria e nem pela coordenação
            query = {
                "startAt": {"$lt": reservation_datetime + timedelta(hours=3)},
                "endAt": {"$gt": reservation_datetime},
                "status": {"$nin": [
                    EventStatus.REJECTED_BY_REITORIA.value,
                    EventStatus.REJECTED_BY_COORDENACAO.value
                ]}
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
        Atualiza um evento existente na coleção de eventos e atualizar o status da reserva.

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
            self.reservation_collection.update_one(
                {"eventId": event_id},
                {"$set": {"status": event_data.get("status")}}
            )
            if result.modified_count > 0:
                return event_id
            else:
                # Se nenhum documento foi modificado, pode significar que os dados são idênticos
                return event_id
        except Exception as e:
            # log the error
            AppLogger.log(Logmessage.UPDATING_EVENT_STATUS, LogType.ERROR,
                          event_id=event_id, reservation_id=event_data.get("reservationId"),
                          status=event_data.get("status"))
            raise e

    def insert_pdf(self, pdf_data):
        try:
            existing = self.pdfs_collection.find_one({"eventId": str(pdf_data.get("eventId"))})

            if existing:
                self.pdfs_collection.replace_one({"_id": existing["_id"]}, pdf_data)
                return str(existing["_id"])
            else:
                result = self.pdfs_collection.insert_one(pdf_data)
                return str(result.inserted_id)

        except Exception as e:
            raise e

    def get_pdf_by_event_id(self, event_id):
        return self.pdfs_collection.find_one({"eventId": str(event_id)})

    def insert_send_email(self,token,step,eventId):
        document = {
            'tokenId': token,
            'step':int(step),
            'eventId':eventId,
            'created_at': datetime.now(),
            'active': True,
            'update_at': datetime.now(),
            'action' : 'waiting'
        }
        result = self.send_email_collection.insert_one(document)
        return str(result.inserted_id)
