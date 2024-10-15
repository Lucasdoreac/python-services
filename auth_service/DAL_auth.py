from datetime import datetime,timedelta
from auth_service.BaseRepository import BaseRepository


class AuthenticationRepository(BaseRepository):

    def get_collection_name(self):
        return self.db.authentications

    def insert_authentication(self, email, token, expires_at):
        """Inserts a new authentication record into the database."""
        record = {
            "email": email,
            "hash": token,
            "expiresAt": expires_at
        }
        return self.get_collection_name().insert_one(record).inserted_id

    def validate_authentication(self, email, token):
        """Checks if an authentication record matches the given email and hash and is not expired."""
        current_time = datetime.now()
        query = {
            "email": email,
            "hash": token,
            "expiresAt": {"$gt": current_time}
        }
        return self.get_collection_name().find_one(query) is not None





