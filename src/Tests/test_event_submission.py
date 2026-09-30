"""Atomic reservation and event submission contract used by the SPA."""

import itertools

import pytest
from bson import ObjectId
from flask import jsonify
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory
from DAL.reservation_manager import ACTIVE_RESERVATION_STATUSES
from SLL import create_app


OWNER = "owner@udf.edu.br"
OTHER = "other@udf.edu.br"
EVENT = {
    "tituloEvento": "Palestra de Extensão",
    "classificacao": "lecture",
    "odsId": "1",
    "descricaoEvento": "Descrição",
    "status": "draft",
}
_slots = itertools.count(1)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    MongoDBConnectionFactory._client = MongoClient()
    MongoDBConnectionFactory._database = "labtech_test"
    import BLL.index as bll_index
    from DAL import (
        BuildingsRepository,
        ReservationsRepository,
        RoomsRepository,
        TypesRepository,
        UniversityRepository,
    )

    bll_index.university_repository = UniversityRepository()
    bll_index.buildings_repository = BuildingsRepository()
    bll_index.rooms_repository = RoomsRepository()
    bll_index.types_repository = TypesRepository()
    bll_index.reservations_repository = ReservationsRepository()
    bll_index.events_repository = bll_index.EventsRepository()
    monkeypatch.setattr("SLL.auth_decorators.requests.get", lambda *args, **kwargs: True)
    app = create_app(get_config())
    monkeypatch.setattr("SLL.events_routes.pdf.generate_event_pdf", lambda **kwargs: None)
    monkeypatch.setattr("SLL.events_routes.send_to_coordenacao", lambda **kwargs: None)
    monkeypatch.setattr("SLL.events_routes.send_reservation_info_to_reitoria", lambda **kwargs: None)
    with app.app_context():
        yield app.test_client()


def headers(email):
    return {"email": email, "token": "test-token"}


def create_draft(client, owner=OWNER):
    response = client.post("/events", json=EVENT, headers=headers(owner))
    assert response.status_code == 200, response.get_json()
    return response.get_json()["eventId"]


def slot():
    day = next(_slots)
    return {
        "roomId": f"test-room-{day}",
        "reservationDate": f"2031-03-{day:02d}T10:00:00.000Z",
    }


def event_document(event_id):
    return MongoDBConnectionFactory.get_db().events.find_one(
        {"_id": ObjectId(event_id)}
    )


def reservations(event_id):
    return list(
        MongoDBConnectionFactory.get_db().reservations.find({"eventId": event_id})
    )


def test_app_creates_partial_unique_index_for_active_reservations(client):
    indexes = MongoDBConnectionFactory.get_db().reservations.index_information()

    index = indexes["uniq_active_reservation_room_start"]
    assert index["key"] == [("roomId", 1), ("startAt", 1)]
    assert index["unique"] is True
    assert index["partialFilterExpression"] == {
        "status": {"$in": ACTIVE_RESERVATION_STATUSES}
    }


def test_owner_can_submit_and_reserve_in_one_request(client):
    event_id = create_draft(client)

    response = client.post(
        f"/events/{event_id}/submit",
        json={**EVENT, **slot()},
        headers=headers(OWNER),
    )

    assert response.status_code == 200, response.get_json()
    assert len(reservations(event_id)) == 1
    assert event_document(event_id)["status"] == "waiting"


def test_failed_event_update_rolls_back_new_reservation(client, monkeypatch):
    event_id = create_draft(client)
    from BLL import FlowController

    monkeypatch.setattr(
        FlowController,
        "update_event",
        staticmethod(lambda *args, **kwargs: (jsonify({"error": "failed"}), 500)),
    )

    response = client.post(
        f"/events/{event_id}/submit",
        json={**EVENT, **slot()},
        headers=headers(OWNER),
    )

    assert response.status_code == 500
    assert reservations(event_id) == []
    assert event_document(event_id)["status"] == "draft"


def test_other_user_cannot_submit_or_update_event(client):
    event_id = create_draft(client)

    submit = client.post(
        f"/events/{event_id}/submit",
        json={**EVENT, **slot()},
        headers=headers(OTHER),
    )
    update = client.put(
        f"/events/{event_id}",
        json={**EVENT, "tituloEvento": "Alterado"},
        headers=headers(OTHER),
    )

    assert submit.status_code == 403
    assert update.status_code == 403
    assert event_document(event_id)["status"] == "draft"
    assert reservations(event_id) == []


def test_conflict_returns_409_without_submitting_second_event(client):
    first_id = create_draft(client)
    second_id = create_draft(client)
    selected_slot = slot()
    first = client.post(
        f"/events/{first_id}/submit",
        json={**EVENT, **selected_slot},
        headers=headers(OWNER),
    )
    second = client.post(
        f"/events/{second_id}/submit",
        json={**EVENT, **selected_slot},
        headers=headers(OWNER),
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert event_document(second_id)["status"] == "draft"
    assert reservations(second_id) == []


def test_retry_reuses_existing_active_reservation(client):
    event_id = create_draft(client)
    selected_slot = slot()
    old_flow = client.post(
        "/reservations",
        json={"eventId": event_id, **selected_slot},
        headers=headers(OWNER),
    )

    response = client.post(
        f"/events/{event_id}/submit",
        json={**EVENT, **selected_slot},
        headers=headers(OWNER),
    )

    assert old_flow.status_code == 201
    assert response.status_code == 200
    assert len(reservations(event_id)) == 1


def test_submit_requires_room_and_reservation_date(client):
    event_id = create_draft(client)

    response = client.post(
        f"/events/{event_id}/submit",
        json=EVENT,
        headers=headers(OWNER),
    )

    assert response.status_code == 400
    assert reservations(event_id) == []
    assert event_document(event_id)["status"] == "draft"
