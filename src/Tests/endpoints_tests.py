import pytest
from mongomock import MongoClient

from configmodule import get_config
from SLL import create_app


# Fixture to create an app with test context
@pytest.fixture
def app(monkeypatch):
    # Setting MonkeyPatch to replace MongoClient
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)

    app = create_app(get_config())
    with app.app_context():
        yield app


# Fixture to create a Flask test client
@pytest.fixture
def client(app):
    return app.test_client()


class TestEndpoints:

    def test_register_reservation_succesfuly(self, monkeypatch, client):


        # Load the data
        payload = {
            "room_id": "661945b2e764a62988bbcf3e",
            "course_id": "66193fb3e764a62988bbcf32",
            "date": "2024-04-25",
            "start_time": "10:00:00",
            "end_time": "12:00:00"
        }

        # response, status_code = FlowController.register_reservation_from_json(payload)
        response = client.post('/reservations', json=payload)

        # Check the response and assert for expected behavior
        assert response.status_code == 201
        assert response.get_json() == {'success': "Reservation attempted"}

    def test_register_event_successfully(self, monkeypatch, client):


        # Load the data
        event = {
            "name": "guilherme",
            "organizer": {"phone": "999865850", "name": "guilherme", "email": "guilherme.amaral2004@gmail.com"},
            "eventTypeId": "eventTypeId",
            "odsTypeId": "odsTypeId",
            "subscriptionLink": "subscriptionLink",
            "description": "description",
            "graduationId": "graduationId",
            "targetPublic": "targetPublic",
            "resources": "resources",
            "expectedSubscribers": "expectedSubscribers",
            "roomType": "roomType",
            "entrepreneuralPath": "entrepreneuralPath",
            "extensionProject": "extensionProject",
            "studentsMonitors": ["31891942", "30008021"],
            "eventLogo": "eventLogo"
        }

        # Call the method that should use the mocked function
        response = client.post('/events', json=event)

        # Check the response and assert for expected behavior
        assert response.status_code == 201
        assert response.get_json() == {'success': "Event registration successful"}


