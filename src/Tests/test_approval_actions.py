"""Security regressions for email based event approval actions."""

import pytest
from bson import ObjectId
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory
from SLL import create_app


@pytest.fixture
def approval_client(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    MongoDBConnectionFactory._client = MongoClient()
    MongoDBConnectionFactory._database = "approval_action_test"
    import BLL.index as bll_index
    import BLL.send_emails as send_emails
    from DAL.collections_repositories import EventsRepository, SendEmailrepository

    bll_index.events_repository = EventsRepository()
    send_emails.events_repository = bll_index.events_repository
    send_emails.send_email_repository = SendEmailrepository()
    app = create_app(get_config())
    monkeypatch.setattr("BLL.send_emails.send_email", lambda payload: None)
    with app.app_context():
        yield app.test_client()


def create_approval(approval_client, step=0, action="approve", status="waiting"):
    db = MongoDBConnectionFactory.get_db()
    event_id = str(ObjectId())
    group_id = f"group-{ObjectId()}"
    db.events.insert_one({
        "_id": ObjectId(event_id),
        "status": status,
        "approvalTokenGroups": {str(step): group_id},
        "organizer": {"email": "owner@example.test"},
    })
    db.reservations.insert_one({
        "eventId": event_id,
        "roomId": f"room-{event_id}",
        "startAt": ObjectId(),
        "status": status,
    })
    token_id = f"token-{ObjectId()}"
    db.send_email.insert_one({
        "tokenId": token_id,
        "eventId": event_id,
        "step": step,
        "action": action,
        "groupId": group_id,
        "active": True,
    })
    return event_id, token_id, group_id


def test_get_action_link_only_shows_confirmation_and_post_consumes_once(
    approval_client,
):
    event_id, token_id, _ = create_approval(approval_client)
    db = MongoDBConnectionFactory.get_db()

    preview = approval_client.get(
        "/approve", query_string={"eventId": event_id, "tokenId": token_id}
    )
    assert preview.status_code == 200
    assert b"Confirmar" in preview.data
    assert preview.headers["Cache-Control"] == "no-store"
    assert preview.headers["Referrer-Policy"] == "no-referrer"
    assert db.events.find_one({"_id": ObjectId(event_id)})["status"] == "waiting"
    assert db.send_email.find_one({"tokenId": token_id})["active"] is True

    confirmed = approval_client.post(
        "/approve", data={"eventId": event_id, "tokenId": token_id}
    )
    assert confirmed.status_code == 200
    assert db.events.find_one({"_id": ObjectId(event_id)})["status"] == "approved_by_coordenacao"
    assert db.reservations.find_one({"eventId": event_id})["status"] == "approved_by_coordenacao"
    assert db.send_email.find_one({"tokenId": token_id})["active"] is False

    replay = approval_client.post(
        "/approve", data={"eventId": event_id, "tokenId": token_id}
    )
    assert replay.status_code == 404


def test_approval_emails_issue_distinct_tokens_bound_to_each_action(
    approval_client, monkeypatch
):
    from BLL import send_emails

    event_id, _, _ = create_approval(approval_client)
    db = MongoDBConnectionFactory.get_db()
    existing_token_ids = {record["tokenId"] for record in db.send_email.find({"eventId": event_id})}
    configured_recipients = list(send_emails.emails["coordenacao"])
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setattr(
        send_emails.FlowController,
        "find_event_by_event_id",
        lambda _event_id: {"graduationId": "course-1"},
    )
    monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda _id: "teacher-1")
    monkeypatch.setattr(send_emails, "find_teacher_email_by_id", lambda _id: "coord@example.test")

    coordination_html = send_emails.send_to_coordenacao(event_id)
    coordination_tokens = [
        record for record in db.send_email.find({"eventId": event_id, "step": 0})
        if record["tokenId"] not in existing_token_ids
    ]
    assert {token["action"] for token in coordination_tokens} == {
        "approve", "reject"
    }
    assert len({token["tokenId"] for token in coordination_tokens}) == 2
    assert all(token["groupId"] == coordination_tokens[0]["groupId"] for token in coordination_tokens)
    assert db.send_email.find_one({"tokenId": next(iter(existing_token_ids))})["active"] is False
    assert db.events.find_one({"_id": ObjectId(event_id)})["approvalTokenGroups"]["0"] == coordination_tokens[0]["groupId"]
    assert send_emails.emails["coordenacao"] == configured_recipients
    for token in coordination_tokens:
        assert token["tokenId"] in coordination_html

    first_group_token = coordination_tokens[0]["tokenId"]
    send_emails.send_to_coordenacao(event_id)
    assert all(
        not token["active"]
        for token in db.send_email.find({"eventId": event_id, "groupId": coordination_tokens[0]["groupId"]})
    )
    current_group = db.events.find_one({"_id": ObjectId(event_id)})["approvalTokenGroups"]["0"]
    assert current_group != coordination_tokens[0]["groupId"]
    assert db.send_email.find_one({"tokenId": first_group_token})["active"] is False
    assert send_emails.emails["coordenacao"] == configured_recipients

    db.events.update_one(
        {"_id": ObjectId(event_id)}, {"$set": {"status": "approved_by_coordenacao"}}
    )
    reitoria_html = send_emails.send_to_reitoria(event_id)
    assert isinstance(reitoria_html, str)
    reitoria_tokens = list(db.send_email.find({"eventId": event_id, "step": 1}))
    assert {token["action"] for token in reitoria_tokens} == {"approve", "reject"}, list(db.send_email.find({"eventId": event_id}))
    assert len({token["tokenId"] for token in reitoria_tokens}) == 2
    assert all(token["groupId"] == reitoria_tokens[0]["groupId"] for token in reitoria_tokens)
    for token in reitoria_tokens:
        assert token["tokenId"] in reitoria_html


def test_coordinator_recipients_do_not_leak_between_events(approval_client, monkeypatch):
    from unittest.mock import Mock
    from BLL import send_emails

    first_event, _, _ = create_approval(approval_client)
    second_event, _, _ = create_approval(approval_client)
    captured_payloads = []
    monkeypatch.setitem(send_emails.emails, "coordenacao", [])
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setattr(
        send_emails.FlowController,
        "find_event_by_event_id",
        lambda event_id: {"graduationId": event_id},
    )
    monkeypatch.setattr(
        send_emails,
        "get_coordinator_by_graduation_id",
        lambda course_id: f"teacher-{course_id}",
    )
    monkeypatch.setattr(
        send_emails,
        "find_teacher_email_by_id",
        lambda teacher_id: f"{teacher_id}@example.test",
    )
    monkeypatch.setattr(
        send_emails,
        "send_email",
        lambda payload: captured_payloads.append(payload) or Mock(status_code=200),
    )

    send_emails.send_to_coordenacao(first_event)
    send_emails.send_to_coordenacao(second_event)

    assert len(captured_payloads) == 2
    assert captured_payloads[0]["to"] == f"teacher-{first_event}@example.test"
    assert captured_payloads[1]["to"] == f"teacher-{second_event}@example.test"


@pytest.mark.parametrize("path,other_action", [("/reject", "approve"), ("/approve", "reject")])
def test_action_token_cannot_be_used_for_another_action(
    approval_client, path, other_action
):
    event_id, token_id, _ = create_approval(approval_client, action=other_action)
    response = approval_client.post(
        path, data={"eventId": event_id, "tokenId": token_id}
    )
    assert response.status_code == 404
    assert MongoDBConnectionFactory.get_db().events.find_one(
        {"_id": ObjectId(event_id)}
    )["status"] == "waiting"


def test_token_is_bound_to_event_and_current_approval_stage(approval_client):
    event_id, token_id, _ = create_approval(approval_client)
    other_event_id, _, _ = create_approval(approval_client)
    wrong_event = approval_client.post(
        "/approve", data={"eventId": other_event_id, "tokenId": token_id}
    )
    assert wrong_event.status_code == 404

    db = MongoDBConnectionFactory.get_db()
    db.events.update_one(
        {"_id": ObjectId(event_id)}, {"$set": {"status": "approved_by_coordenacao"}}
    )
    stale_stage = approval_client.post(
        "/approve", data={"eventId": event_id, "tokenId": token_id}
    )
    assert stale_stage.status_code == 404
    assert db.send_email.find_one({"tokenId": token_id})["active"] is True


def test_stage_comes_from_token_and_conflicting_action_cannot_win(approval_client):
    event_id, approve_token, group_id = create_approval(approval_client, action="approve")
    reject_token = f"token-{ObjectId()}"
    MongoDBConnectionFactory.get_db().send_email.insert_one({
        "tokenId": reject_token,
        "eventId": event_id,
        "step": 0,
        "action": "reject",
        "groupId": group_id,
        "active": True,
    })

    approved = approval_client.post(
        "/approve?who=reitoria",
        data={"eventId": event_id, "tokenId": approve_token},
    )
    assert approved.status_code == 200
    assert MongoDBConnectionFactory.get_db().events.find_one(
        {"_id": ObjectId(event_id)}
    )["status"] == "approved_by_coordenacao"

    rejected_after_approval = approval_client.post(
        "/reject", data={"eventId": event_id, "tokenId": reject_token}
    )
    assert rejected_after_approval.status_code == 404
    assert MongoDBConnectionFactory.get_db().events.find_one(
        {"_id": ObjectId(event_id)}
    )["status"] == "approved_by_coordenacao"


def test_reitoria_token_only_works_at_reitoria_stage(approval_client):
    event_id, token_id, _ = create_approval(
        approval_client, step=1, action="reject", status="approved_by_coordenacao"
    )
    response = approval_client.post(
        "/reject", data={"eventId": event_id, "tokenId": token_id}
    )
    assert response.status_code == 200
    db = MongoDBConnectionFactory.get_db()
    assert db.events.find_one({"_id": ObjectId(event_id)})["status"] == "rejected_by_reitoria"
    assert db.send_email.find_one({"tokenId": token_id})["active"] is False


def test_request_changes_is_hidden_and_disabled_until_issue_35(approval_client, monkeypatch):
    from BLL import send_emails

    event_id, _, _ = create_approval(approval_client)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setattr(
        send_emails.FlowController,
        "find_event_by_event_id",
        lambda _event_id: {"graduationId": "course-1"},
    )
    monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda _id: "teacher-1")
    monkeypatch.setattr(send_emails, "find_teacher_email_by_id", lambda _id: "coord@example.test")
    email_html = send_emails.send_to_coordenacao(event_id)
    assert "Solicitar alterações" not in email_html
    assert "/request_changes" not in email_html

    response = approval_client.get(
        "/request_changes", query_string={"eventId": event_id, "tokenId": "old-token"}
    )
    assert response.status_code == 410
    assert MongoDBConnectionFactory.get_db().events.find_one(
        {"_id": ObjectId(event_id)}
    )["status"] == "waiting"


def test_failed_reservation_transition_restores_event_and_token(approval_client):
    event_id, token_id, group_id = create_approval(approval_client)
    db = MongoDBConnectionFactory.get_db()
    db.reservations.update_one(
        {"eventId": event_id}, {"$set": {"status": "rejected_by_coordenacao"}}
    )

    response = approval_client.post(
        "/approve", data={"eventId": event_id, "tokenId": token_id}
    )

    assert response.status_code == 409
    assert db.events.find_one({"_id": ObjectId(event_id)})["status"] == "waiting"
    assert db.events.find_one({"_id": ObjectId(event_id)})["approvalTokenGroups"]["0"] == group_id
    assert db.send_email.find_one({"tokenId": token_id})["active"] is True
