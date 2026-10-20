from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from time import monotonic, sleep
from uuid import uuid4

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


# Statuses in which the organizer may still edit or submit an event. Events
# stored without a status are drafts.
EDITABLE_EVENT_STATUSES = frozenset({EventStatus.DRAFT.value, EventStatus.REQUESTED_CHANGE.value})


class EventNotEditable(Exception):
    """O evento mudou de status e não aceita mais edição ou envio."""


class ReservationConflict(ValueError):
    """A sala já está reservada no horário solicitado."""


class ReservationLockTimeout(RuntimeError):
    """Não foi possível serializar a operação de reserva a tempo."""


class ReservationManager:
    _LOCK_LEASE = timedelta(seconds=120)
    _LOCK_WAIT_SECONDS = 30
    _LOCK_RETRY_SECONDS = 0.025

    @staticmethod
    def ensure_indexes():
        """Create a database-level backstop for identical active start times.

        ``insert_reservation`` serializes interval checks per room; the index
        also protects duplicate starts if another writer bypasses that method.
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
        self.reservation_locks_collection = self.db.reservation_locks
        self.rooms_collection = self.db.rooms
        self.buildings_collection = self.db.buildings
        self.events_collection = self.db.events
        self.pdfs_collection = self.db.pdfs
        self.send_email_collection = self.db.send_email

    @staticmethod
    def _reservation_lock_id(room_id):
        return f"room:{room_id}"

    def _acquire_reservation_lock(self, room_id):
        lock_id = self._reservation_lock_id(room_id)
        owner = uuid4().hex
        deadline = monotonic() + self._LOCK_WAIT_SECONDS

        while True:
            now = datetime.now(timezone.utc)
            expires_at = now + self._LOCK_LEASE
            renewed = self.reservation_locks_collection.update_one(
                {"_id": lock_id, "leaseExpiresAt": {"$lte": now}},
                {"$set": {"owner": owner, "leaseExpiresAt": expires_at}},
            )
            if renewed.modified_count:
                return lock_id, owner

            try:
                self.reservation_locks_collection.insert_one(
                    {"_id": lock_id, "owner": owner, "leaseExpiresAt": expires_at}
                )
                return lock_id, owner
            except DuplicateKeyError:
                # Another API process owns this room lock, or acquired it first.
                pass

            if monotonic() >= deadline:
                raise ReservationLockTimeout(
                    "Could not acquire the room reservation lock; retry the request."
                )
            sleep(self._LOCK_RETRY_SECONDS)

    def _owns_reservation_lock(self, lock_id, owner):
        return self.reservation_locks_collection.find_one(
            {
                "_id": lock_id,
                "owner": owner,
                "leaseExpiresAt": {"$gt": datetime.now(timezone.utc)},
            },
            {"_id": 1},
        ) is not None

    def _release_reservation_lock(self, lock_id, owner):
        self.reservation_locks_collection.delete_one(
            {"_id": lock_id, "owner": owner}
        )

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

        lock_id, owner = self._acquire_reservation_lock(room_id)
        try:
            conflict = self.reservation_collection.find_one({
                "roomId": room_id,
                "startAt": {"$lt": reservation_end_time},
                "endAt": {"$gt": reservation_start_time},
                "status": {"$in": ACTIVE_RESERVATION_STATUSES},
            })
            if conflict:
                raise ReservationConflict("This time slot is already booked.")

            if not self._owns_reservation_lock(lock_id, owner):
                raise ReservationLockTimeout(
                    "The room reservation lock expired; retry the request."
                )

            reservation = {
                "roomId": room_id,
                "eventId": event_id,  # Armazena o eventId no documento
                "startAt": reservation_start_time,
                "endAt": reservation_end_time,
                "status": EventStatus.WAITING.value,
            }

            try:
                result = self.reservation_collection.insert_one(reservation)
            except DuplicateKeyError as error:
                raise ReservationConflict("This time slot is already booked.") from error

            if not self._owns_reservation_lock(lock_id, owner):
                self.reservation_collection.delete_one({"_id": result.inserted_id})
                raise ReservationLockTimeout(
                    "The room reservation lock expired; retry the request."
                )
            return reservation
        finally:
            self._release_reservation_lock(lock_id, owner)

    def find_active_reservation(self, event_id, room_id, start_at):
        return self.reservation_collection.find_one({
            "eventId": event_id,
            "roomId": room_id,
            "startAt": start_at,
            "status": {"$in": ACTIVE_RESERVATION_STATUSES},
        })

    def delete_reservation(self, reservation_id):
        self.reservation_collection.delete_one({"_id": reservation_id})

    def find_reservation_ids_of_event(self, event_id):
        return [r["_id"] for r in self.reservation_collection.find({"eventId": event_id}, {"_id": 1})]

    def delete_reservations(self, reservation_ids):
        if reservation_ids:
            self.reservation_collection.delete_many({"_id": {"$in": list(reservation_ids)}})

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
            print(f"Erro na busca: {type(e).__name__}")
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

    def update_event(self, event_id: str, event_data: Dict[str, Any], from_statuses=None):
        """
        Atualiza um evento existente na coleção de eventos e atualizar o status da reserva.

        Args:
            event_id (str): ID do evento a ser atualizado.
            event_data (dict): Dicionário contendo os dados atualizados do evento.
            from_statuses (iterable | None): status em que o evento precisa estar para esta
                gravação valer. Sem valor, só eventos editáveis (rascunho ou com alterações
                pedidas); as decisões de aprovação informam o status da etapa.

        Returns:
            str: ID do evento atualizado, útil para confirmação.

        Raises:
            EventNotEditable: o evento já não está em nenhum dos status aceitos.
            Exception: Repassa exceções ocorridas durante a atualização no banco de dados.
        """
        try:
            from bson import ObjectId
            from pymongo import ReturnDocument
            accepted = list(EDITABLE_EVENT_STATUSES if from_statuses is None else from_statuses)
            if from_statuses is None:
                accepted.append(None)  # evento sem status é rascunho
            # O status faz parte do filtro: a checagem e a gravação são uma só operação,
            # então um envio ou uma aprovação concorrente faz esta gravação não casar com nada.
            # O documento anterior diz qual status restaurar se a gravação da reserva falhar.
            before = self.events_collection.find_one_and_update(
                {"_id": ObjectId(event_id), "status": {"$in": accepted}},
                {"$set": event_data},
                projection={"status": 1},
                return_document=ReturnDocument.BEFORE,
            )
            if before is None:
                raise EventNotEditable(event_id)
            try:
                self.reservation_collection.update_many(
                    {"eventId": event_id},
                    {"$set": {"status": event_data.get("status")}}
                )
            except Exception:
                # Evento e reserva são gravações separadas: se a da reserva falhar, devolve o
                # status do evento (só enquanto ele ainda tem o valor gravado aqui), para que os
                # dois nunca divirjam, e a falha segue como antes.
                self._restore_event_status(event_id, event_data.get("status"), before.get("status"))
                raise
            return event_id
        except EventNotEditable:
            raise
        except Exception as e:
            # log the error
            AppLogger.log(Logmessage.UPDATING_EVENT_STATUS, LogType.ERROR,
                          event_id=event_id, reservation_id=event_data.get("reservationId"),
                          status=event_data.get("status"))
            raise e

    def _restore_event_status(self, event_id, written_status, previous_status):
        from bson import ObjectId
        change = {"$set": {"status": previous_status}} if previous_status is not None else {"$unset": {"status": ""}}
        try:
            self.events_collection.update_one(
                {"_id": ObjectId(event_id), "status": written_status}, change)
        except Exception as error:  # a falha original é a que deve ser informada
            AppLogger.log(Logmessage.UPDATING_EVENT_STATUS, LogType.ERROR,
                          event_id=event_id, reservation_id=None, status=f"restore failed: {type(error).__name__}")

    def rollback_approval_start(self, event_id, expected_status, previous_status):
        """Devolve o evento ao status editável quando o aviso de aprovação não pôde ser enviado.

        Só desfaz enquanto o evento ainda está em ``expected_status`` (o que esta submissão
        gravou); revoga também os links de aprovação já emitidos, para que um e-mail que
        talvez tenha saído não decida um evento que voltou a ser rascunho.
        """
        from bson import ObjectId

        previous_change = (
            {"$set": {"status": previous_status}}
            if previous_status is not None
            else {"$unset": {"status": ""}}
        )
        restored = self.events_collection.update_one(
            {"_id": ObjectId(event_id), "status": expected_status}, previous_change
        )
        if restored.matched_count != 1:
            return False

        try:
            self.reservation_collection.update_many(
                {"eventId": event_id, "status": expected_status}, previous_change
            )
            self.send_email_collection.update_many(
                {"eventId": event_id, "active": True},
                {"$set": {"active": False, "revoked_at": datetime.now()}},
            )
        except Exception:
            self._restore_event_status(event_id, previous_status, expected_status)
            raise
        return True

    def insert_pdf(self, pdf_data):
        try:
            existing = self.pdfs_collection.find_one({"path": pdf_data.get("path")})

            if existing:
                self.pdfs_collection.replace_one({"_id": existing["_id"]}, pdf_data)
                return str(existing["_id"])
            else:
                result = self.pdfs_collection.insert_one(pdf_data)
                return str(result.inserted_id)

        except Exception as e:
            raise e

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
