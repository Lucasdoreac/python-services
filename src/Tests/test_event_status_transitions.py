"""The server owns the event status: clients cannot choose approval states."""

import pytest
from bson import ObjectId

from DAL import MongoDBConnectionFactory
from Tests.test_event_submission import (  # noqa: F401
    EVENT, OWNER, client, create_draft, event_document, headers, reservations, slot,
)

APPROVAL_STATES = [
    "waiting", "approved_by_coordenacao", "rejected_by_coordenacao", "approved_by_reitoria",
    "rejected_by_reitoria", "requested_change", "direct_approval", "anything-else",
]


def event_status(event_id):
    return event_document(event_id)["status"]


def reservation_statuses(event_id):
    return sorted(r["status"] for r in reservations(event_id))


def put(client, event_id, **fields):
    return client.put(f"/events/{event_id}", json={**EVENT, **fields}, headers=headers(OWNER))


def submit(client, event_id):
    return client.post(f"/events/{event_id}/submit", json={**EVENT, **slot()}, headers=headers(OWNER))


def force_status(event_id, status):
    db = MongoDBConnectionFactory.get_db()
    db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": status}})
    db.reservations.update_many({"eventId": event_id}, {"$set": {"status": status}})


@pytest.mark.parametrize("status", APPROVAL_STATES)
def test_a_client_cannot_put_an_approval_state(client, status):
    event_id = create_draft(client)
    assert submit(client, event_id).status_code == 200  # draft -> waiting, with a reservation
    before = (event_status(event_id), reservation_statuses(event_id))
    response = put(client, event_id, status=status)
    assert response.status_code in (400, 409), response.get_json()
    assert (event_status(event_id), reservation_statuses(event_id)) == before


@pytest.mark.parametrize("status", APPROVAL_STATES)
def test_a_draft_cannot_be_given_an_approval_state(client, status):
    event_id = create_draft(client)
    assert put(client, event_id, status=status).status_code == 400
    assert event_status(event_id) == "draft"


@pytest.mark.parametrize("status", ["approved_by_reitoria", "direct_approval", "waiting"])
def test_creating_an_event_always_starts_it_as_a_draft(client, status):
    response = client.post("/events", json={**EVENT, "status": status}, headers=headers(OWNER))
    assert response.status_code == 400
    plain = client.post("/events", json={k: v for k, v in EVENT.items() if k != "status"}, headers=headers(OWNER))
    assert plain.status_code == 200 and event_status(plain.get_json()["eventId"]) == "draft"


@pytest.mark.parametrize("state", ["waiting", "approved_by_coordenacao", "approved_by_reitoria",
                                   "rejected_by_coordenacao", "rejected_by_reitoria", "direct_approval"])
def test_an_event_past_the_draft_cannot_be_edited_or_submitted_again(client, state):
    event_id = create_draft(client)
    assert submit(client, event_id).status_code == 200
    force_status(event_id, state)
    before = (event_status(event_id), reservation_statuses(event_id), len(reservations(event_id)))
    assert put(client, event_id, tituloEvento="Another title").status_code == 409
    assert put(client, event_id, status="requested").status_code == 409
    assert submit(client, event_id).status_code == 409
    assert (event_status(event_id), reservation_statuses(event_id), len(reservations(event_id))) == before


def test_a_draft_can_still_be_edited_and_stays_a_draft(client):
    event_id = create_draft(client)
    assert put(client, event_id, tituloEvento="New title").status_code == 200
    assert put(client, event_id, status="draft").status_code == 200
    plain = {k: v for k, v in EVENT.items() if k != "status"}
    assert client.put(f"/events/{event_id}", json=plain, headers=headers(OWNER)).status_code == 200
    assert event_status(event_id) == "draft"


def test_submitting_a_draft_starts_the_approval_that_matches_its_type(client):
    lecture = create_draft(client)
    assert put(client, lecture, status="requested", classificacao="lecture").status_code == 200
    assert event_status(lecture) == "waiting"

    exam = client.post("/events", json={**EVENT, "classificacao": "exam"}, headers=headers(OWNER)).get_json()["eventId"]
    assert put(client, exam, status="requested", classificacao="exam").status_code == 200
    assert event_status(exam) == "direct_approval"


def test_requesting_an_unsupported_type_is_not_stored_as_a_status(client):
    event_id = create_draft(client)
    response = put(client, event_id, status="requested", classificacao="something-else")
    assert response.status_code == 400
    assert event_status(event_id) == "draft"


def test_after_a_change_request_the_organizer_edits_and_resubmits(client):
    event_id = create_draft(client)
    assert submit(client, event_id).status_code == 200
    force_status(event_id, "requested_change")
    assert put(client, event_id, tituloEvento="Reworked").status_code == 200
    assert event_status(event_id) == "requested_change"  # editing does not change the stored status
    assert put(client, event_id, status="requested", classificacao="lecture").status_code == 200
    assert event_status(event_id) == "waiting"
