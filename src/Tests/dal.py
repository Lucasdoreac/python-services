# tests/dal.py
import mongomock
import pytest
# Mocking pymongo.MongoClient with mongomock.MongoClient globally before importing any modules.
# This ensures that any use of MongoClient in the imported modules will automatically use the mocked version.
# It is essential to perform this mock before imports to prevent any real database connections
# from being established during module initialization, which can occur if MongoClient is instantiated
# at the module level or within class definitions. This approach ensures all database interactions
# are mocked, providing a consistent, isolated testing environment without side effects.
pytest.MonkeyPatch().setattr('pymongo.MongoClient', mongomock.MongoClient)
from DAL.mongodb_factory import MongoDBConnectionFactory


class TestMongoDBConnectionFactory:
    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch):
        """Setup a mongomock patch and environment variables before each test method."""
        # Mock load_variables to return a specific configuration
        test_config = {
            "uri": "mongodb://localhost:27017/",  # URI is fine for mongomock
            "database": "test_db"
        }
        monkeypatch.setattr('DAL.index.load_variables', lambda: test_config)

    def test_singleton_client_instance(self):
        """Test that the MongoDBConnectionFactory returns the same client instance."""
        client1 = MongoDBConnectionFactory.get_db().client
        client2 = MongoDBConnectionFactory.get_db().client
        assert client1 is client2, "MongoDBConnectionFactory should return the same MongoClient instance."

    def test_database_access(self):
        """Test that the MongoDBConnectionFactory returns a valid database instance."""
        db = MongoDBConnectionFactory.get_db()
        assert db.name == 'test_db', "Should access the correct database."

    def test_data_retrieval(self):
        """Test retrieving data from a known collection."""
        db = MongoDBConnectionFactory.get_db()
        db['test_collection'].insert_one({'name': 'test_item'})
        count = db['test_collection'].count_documents({})
        assert count == 1, "Should retrieve data from 'test_collection'."

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        # Reset the client after each test to avoid shared state between tests
        yield
        MongoDBConnectionFactory._client = None
