from datetime import datetime, timedelta
from .base_repository import BaseRepository


class UniversityRepository(BaseRepository):
    def get_collection_name(self):
        return self.db.universities


class BuildingsRepository(BaseRepository):
    def get_collection_name(self):
        return self.db["buildings"]


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



