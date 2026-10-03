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
    monkeypatch.setattr("SLL.auth_upstream.requests.get", lambda *args, **kwargs: True)
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
    # An earlier attempt already holds the slot for this event (the standalone
    # POST /reservations that used to create it was removed).
    from BLL import FlowController

    FlowController.reserve_for_event(event_id, selected_slot["roomId"], selected_slot["reservationDate"])

    response = client.post(
        f"/events/{event_id}/submit",
        json={**EVENT, **selected_slot},
        headers=headers(OWNER),
    )

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


# --- a resubmission after a change request must not leave two reservations -----------------

def request_changes_on(event_id):
    db = MongoDBConnectionFactory.get_db()
    db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {
        "status": "requested_change", "changeRequest": {"message": "x", "by": "coordenacao"}}})
    db.reservations.update_many({"eventId": event_id}, {"$set": {"status": "requested_change"}})


def test_resubmit_with_another_room_replaces_the_reservation(client):
    event_id = create_draft(client)
    first, second = slot(), slot()
    assert client.post(f"/events/{event_id}/submit", json={**EVENT, **first}, headers=headers(OWNER)).status_code == 200
    request_changes_on(event_id)

    response = client.post(f"/events/{event_id}/submit", json={**EVENT, **second}, headers=headers(OWNER))

    assert response.status_code == 200, response.get_json()
    held = reservations(event_id)
    assert [r["roomId"] for r in held] == [second["roomId"]]
    assert held[0]["status"] == "waiting" and event_document(event_id)["status"] == "waiting"
    # the first room is free again for another event
    other = create_draft(client, OTHER)
    assert client.post(f"/events/{other}/submit", json={**EVENT, **first}, headers=headers(OTHER)).status_code == 200


def test_resubmit_into_a_taken_room_keeps_the_old_reservation(client):
    event_id, rival = create_draft(client), create_draft(client, OTHER)
    first, taken = slot(), slot()
    assert client.post(f"/events/{event_id}/submit", json={**EVENT, **first}, headers=headers(OWNER)).status_code == 200
    assert client.post(f"/events/{rival}/submit", json={**EVENT, **taken}, headers=headers(OTHER)).status_code == 200
    request_changes_on(event_id)

    response = client.post(f"/events/{event_id}/submit", json={**EVENT, **taken}, headers=headers(OWNER))

    assert response.status_code == 409
    assert [r["roomId"] for r in reservations(event_id)] == [first["roomId"]]
    assert event_document(event_id)["status"] == "requested_change"


def test_a_failed_resubmission_keeps_the_old_reservation(client, monkeypatch):
    from BLL import FlowController

    event_id = create_draft(client)
    first, second = slot(), slot()
    assert client.post(f"/events/{event_id}/submit", json={**EVENT, **first}, headers=headers(OWNER)).status_code == 200
    request_changes_on(event_id)
    monkeypatch.setattr(FlowController, "update_event",
                        staticmethod(lambda *a, **k: (jsonify({"error": "failed"}), 500)))

    response = client.post(f"/events/{event_id}/submit", json={**EVENT, **second}, headers=headers(OWNER))

    assert response.status_code == 500
    assert [r["roomId"] for r in reservations(event_id)] == [first["roomId"]]


def test_status_update_reaches_every_reservation_of_the_event(client):
    from DAL.reservation_manager import ReservationManager

    event_id = create_draft(client)
    db = MongoDBConnectionFactory.get_db()
    for room in ("legacy-a", "legacy-b"):
        db.reservations.insert_one({"eventId": event_id, "roomId": room, "status": "draft"})
    ReservationManager().update_event(event_id, {"status": "waiting"})
    assert {r["status"] for r in reservations(event_id)} == {"waiting"}


def test_the_organizer_can_resubmit_after_a_change_request(client):
    event_id = create_draft(client)
    chosen = slot()
    assert client.post(f"/events/{event_id}/submit", json={**EVENT, **chosen}, headers=headers(OWNER)).status_code == 200
    request_changes_on(event_id)
    response = client.post(f"/events/{event_id}/submit", json={**EVENT, **chosen}, headers=headers(OWNER))
    assert response.status_code == 200, response.get_json()
    assert event_document(event_id)["status"] == "waiting" and len(reservations(event_id)) == 1


def test_put_cannot_write_status_or_change_request(client):
    event_id = create_draft(client)
    assert client.post(f"/events/{event_id}/submit", json={**EVENT, **slot()}, headers=headers(OWNER)).status_code == 200
    request_changes_on(event_id)
    client.put(f"/events/{event_id}", json={**EVENT, "status": "approved_by_reitoria",
                                           "changeRequest": {"message": "forged"}}, headers=headers(OWNER))
    event = event_document(event_id)
    assert event["status"] == "requested_change"
    assert event["changeRequest"]["message"] == "x"


# --- two resubmissions racing for the same event --------------------------------------------

def resubmit_racing(client, monkeypatch, event_id, outer_slot, inner_slot):
    """Run a whole second resubmission after the first one read the event's reservations.

    The outer request has passed the status gate and listed the old reservations; the inner
    one then completes before the outer request inserts its own reservation and writes the event.
    """
    from BLL import FlowController

    calls = []
    for name in ("pdf.generate_event_pdf", "send_to_coordenacao"):
        monkeypatch.setattr(f"SLL.events_routes.{name}", lambda _name=name, **kwargs: calls.append(_name))
    real = FlowController.reservation_ids_of_event
    state = {}

    def list_then_race(event):
        previous = real(event)
        if not state:
            state["inner"] = None  # the nested request must not race again
            state["inner"] = client.post(
                f"/events/{event}/submit", json={**EVENT, **inner_slot}, headers=headers(OWNER))
        return previous

    monkeypatch.setattr(FlowController, "reservation_ids_of_event", staticmethod(list_then_race))
    outer = client.post(f"/events/{event_id}/submit", json={**EVENT, **outer_slot}, headers=headers(OWNER))
    return outer, state["inner"], calls


def test_concurrent_resubmits_keep_only_the_winners_reservation(client, monkeypatch):
    event_id = create_draft(client)
    first, outer_slot, inner_slot = slot(), slot(), slot()
    assert client.post(f"/events/{event_id}/submit", json={**EVENT, **first}, headers=headers(OWNER)).status_code == 200
    request_changes_on(event_id)

    outer, inner, _ = resubmit_racing(client, monkeypatch, event_id, outer_slot, inner_slot)

    assert inner.status_code == 200 and outer.status_code == 409
    held = reservations(event_id)
    assert [r["roomId"] for r in held] == [inner_slot["roomId"]]
    assert held[0]["status"] == event_document(event_id)["status"] == "waiting"
    # both losing slots are free again
    other = create_draft(client, OTHER)
    for freed in (first, outer_slot):
        assert client.post(f"/events/{other}/submit", json={**EVENT, **freed}, headers=headers(OTHER)).status_code == 200
        MongoDBConnectionFactory.get_db().reservations.delete_many({"eventId": other})
        MongoDBConnectionFactory.get_db().events.update_one({"_id": ObjectId(other)}, {"$set": {"status": "draft"}})


def test_the_losing_resubmission_sends_no_notification(client, monkeypatch):
    event_id = create_draft(client)
    assert client.post(f"/events/{event_id}/submit", json={**EVENT, **slot()}, headers=headers(OWNER)).status_code == 200
    request_changes_on(event_id)

    outer, inner, calls = resubmit_racing(client, monkeypatch, event_id, slot(), slot())

    assert (inner.status_code, outer.status_code) == (200, 409)
    assert calls == ["pdf.generate_event_pdf", "send_to_coordenacao"]  # only the winner's
