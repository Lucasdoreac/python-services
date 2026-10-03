"""Edit and submit write only while the stored status still allows it."""

from bson import ObjectId

from DAL import MongoDBConnectionFactory
from Tests.test_event_submission import (  # noqa: F401
    EVENT, OWNER, client, create_draft, event_document, headers, reservations, slot,
)


def set_status_after_gate(monkeypatch, event_id, status):
    """Run the concurrent writer between the status gate and the event write."""
    from SLL import events_routes

    real_gate = events_routes.event_status_gate

    def gate_then_race(*args, **kwargs):
        rejection = real_gate(*args, **kwargs)
        MongoDBConnectionFactory.get_db().events.update_one(
            {"_id": ObjectId(event_id)}, {"$set": {"status": status}}
        )
        return rejection

    monkeypatch.setattr(events_routes, "event_status_gate", gate_then_race)


def side_effects(monkeypatch):
    calls = []
    for name in ("pdf.generate_event_pdf", "send_to_coordenacao", "send_reservation_info_to_reitoria"):
        monkeypatch.setattr(f"SLL.events_routes.{name}", lambda _name=name, **kwargs: calls.append(_name))
    return calls


def test_edit_losing_the_race_returns_409_and_keeps_status(client, monkeypatch):
    event_id = create_draft(client)
    set_status_after_gate(monkeypatch, event_id, "waiting")

    response = client.put(
        f"/events/{event_id}",
        json={**EVENT, "tituloEvento": "Alterado depois do envio"},
        headers=headers(OWNER),
    )

    assert response.status_code == 409
    document = event_document(event_id)
    assert document["status"] == "waiting"
    assert document["name"] != "Alterado depois do envio"


def test_submit_losing_the_race_returns_409_without_side_effects(client, monkeypatch):
    event_id = create_draft(client)
    calls = side_effects(monkeypatch)
    set_status_after_gate(monkeypatch, event_id, "waiting")

    response = client.post(
        f"/events/{event_id}/submit",
        json={**EVENT, **slot()},
        headers=headers(OWNER),
    )

    assert response.status_code == 409
    assert calls == []
    assert reservations(event_id) == []
    assert event_document(event_id)["status"] == "waiting"


def test_edit_and_submit_still_work_while_editable(client, monkeypatch):
    event_id = create_draft(client)
    calls = side_effects(monkeypatch)

    edit = client.put(
        f"/events/{event_id}",
        json={**EVENT, "tituloEvento": "Novo título"},
        headers=headers(OWNER),
    )
    assert edit.status_code == 200
    assert event_document(event_id)["name"] == "Novo título"
    assert event_document(event_id)["status"] == "draft"

    MongoDBConnectionFactory.get_db().events.update_one(
        {"_id": ObjectId(event_id)}, {"$set": {"status": "requested_change"}}
    )
    submit = client.post(
        f"/events/{event_id}/submit", json={**EVENT, **slot()}, headers=headers(OWNER)
    )
    assert submit.status_code == 200
    assert event_document(event_id)["status"] == "waiting"
    assert calls == ["pdf.generate_event_pdf", "send_to_coordenacao"]


def test_event_without_stored_status_is_still_editable(client):
    event_id = create_draft(client)
    MongoDBConnectionFactory.get_db().events.update_one(
        {"_id": ObjectId(event_id)}, {"$unset": {"status": ""}}
    )

    response = client.put(
        f"/events/{event_id}", json={**EVENT, "tituloEvento": "Sem status"}, headers=headers(OWNER)
    )

    assert response.status_code == 200
    assert event_document(event_id)["name"] == "Sem status"


# --- the event and its reservation never disagree when the reservation write fails ----------

def fail_reservation_writes(monkeypatch):
    import mongomock.collection as mc

    def failing(real):
        def write(self, filter, update, *args, **kwargs):
            if self.name == "reservations":
                raise RuntimeError("reservation write failed")
            return real(self, filter, update, *args, **kwargs)
        return write

    # the lane writes the reservation with update_one or update_many depending on the branch
    for name in ("update_one", "update_many"):
        monkeypatch.setattr(mc.Collection, name, failing(getattr(mc.Collection, name)))


def test_a_failed_reservation_write_puts_the_events_status_back(client, monkeypatch):
    from DAL.reservation_manager import ReservationManager

    event_id = create_draft(client)
    MongoDBConnectionFactory.get_db().reservations.insert_one(
        {"eventId": event_id, "roomId": "r1", "status": "draft"})
    fail_reservation_writes(monkeypatch)

    import pytest
    with pytest.raises(RuntimeError):
        ReservationManager().update_event(event_id, {"status": "waiting"})

    assert event_document(event_id)["status"] == "draft"
    assert [r["status"] for r in reservations(event_id)] == ["draft"]


def test_the_restore_does_not_overwrite_a_status_someone_else_set_meanwhile(client, monkeypatch):
    import mongomock.collection as mc
    from DAL.reservation_manager import ReservationManager

    event_id = create_draft(client)
    MongoDBConnectionFactory.get_db().reservations.insert_one(
        {"eventId": event_id, "roomId": "r1", "status": "draft"})
    def racing(real):
        def write(self, filter, update, *args, **kwargs):
            if self.name == "reservations":
                # a concurrent approval moves the event on, then the reservation write fails
                MongoDBConnectionFactory.get_db().events.update_one(
                    {"_id": ObjectId(event_id)}, {"$set": {"status": "approved_by_coordenacao"}})
                raise RuntimeError("reservation write failed")
            return real(self, filter, update, *args, **kwargs)
        return write

    for name in ("update_one", "update_many"):
        monkeypatch.setattr(mc.Collection, name, racing(getattr(mc.Collection, name)))
    import pytest
    with pytest.raises(RuntimeError):
        ReservationManager().update_event(event_id, {"status": "waiting"})

    assert event_document(event_id)["status"] == "approved_by_coordenacao"


def test_submit_with_a_failing_reservation_write_leaves_the_event_in_draft(client, monkeypatch):
    event_id = create_draft(client)
    side_effects(monkeypatch)
    fail_reservation_writes(monkeypatch)

    response = client.post(
        f"/events/{event_id}/submit", json={**EVENT, **slot()}, headers=headers(OWNER))

    assert response.status_code >= 500 or response.status_code == 409, response.status_code
    assert event_document(event_id)["status"] == "draft"
