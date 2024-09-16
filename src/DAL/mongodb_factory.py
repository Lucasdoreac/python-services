from pymongo import MongoClient


class MongoDBConnectionFactory:
    _client = None
    _database = None

    @staticmethod
    def get_db():
        if MongoDBConnectionFactory._client is None:
            raise Exception("MongoDBConnectionFactory has not been initialized")
        return MongoDBConnectionFactory._client[MongoDBConnectionFactory._database]

    @staticmethod
    def init_app(uri, database):
        if MongoDBConnectionFactory._client is None:
            MongoDBConnectionFactory._client = MongoClient(uri)
            MongoDBConnectionFactory._database = database
