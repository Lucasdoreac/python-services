from datetime import datetime, timedelta
from .base_repository import BaseRepository


class UniversityRepository(BaseRepository):
    def get_collection_name(self):
        return self.db.universities


class BuildingsRepository(BaseRepository):
    def get_collection_name(self):
        return self.db["buildings"]

class SendEmailrepository(BaseRepository):
    def get_collection_name(self):
        return self.db.send_email

    def update_one(self, query, updated_fields):
        collection = self.get_collection_name()
        return collection.update_one(query, updated_fields)

    def get_send_email_by_token_id(self, tokenId: str):
        return self.get_collection_name().find_one({"tokenId": tokenId})

    def deactivate_active_for_event_step(self, event_id, step):
        """Revoke all prior email buttons before issuing a replacement set."""
        return self.get_collection_name().update_many(
            {"eventId": event_id, "step": int(step), "active": True},
            {"$set": {"active": False, "revoked_at": datetime.now()}},
        )

class RoomsRepository(BaseRepository):
    def get_collection_name(self):
        return self.db.rooms


class GraduationsRepository(BaseRepository):
    def get_collection_name(self):
        return self.db.graduations


class TypesRepository(BaseRepository):
    def get_collection_name(self):
        return self.db.types

    def get_type_by_collection(self, collection_name):
        return self.convert_id(list(self.types_collection.find({"collection": collection_name})))


class EventsRepository(BaseRepository):
    def get_collection_name(self):
        return self.db.events


class ReservationsRepository(BaseRepository):
    def get_collection_name(self):
        return self.db.reservations
    def get_reservation_by_date(self, date):
        end_date = date + timedelta(days=1)
        query = {
            "startAt": {
                "$gte": date,
                "$lt": end_date
            }

        }
        return self.convert_id(list(self.get_collection_name().find(query)))

    def find_by_query(self, query):
        collection = self.get_collection_name()
        return collection.find_one(query)
