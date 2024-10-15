from abc import ABC,abstractmethod
from bson import ObjectId
from auth_service.mongo import MongoDBConnectionFactory


class BaseRepository(ABC):
    def __init__(self):
        self.db = MongoDBConnectionFactory.get_db()
        self.types_collection = self.db.types
        # self.collection = self.db[self.get_collection_name()]

    @abstractmethod
    def get_collection_name(self):
        """Method to get the specific collection used by the repository."""
        pass

    def find_all(self):
        return self.convert_id(list(self.get_collection_name().find({})))

    def find_by_id(self, _id):
        result = self.get_collection_name().find_one({'_id': ObjectId(_id)})
        return self.convert_id(result)

    @staticmethod
    def convert_id(data):
        """Convert ObjectId to string for JSON serialization."""

        def convert(document):
            for key, value in document.items():
                if isinstance(value, ObjectId):
                    document[key] = str(value)
            return document

        if isinstance(data, list):
            return [convert(doc) for doc in data]
        elif isinstance(data, dict):
            return convert(data)
        return data