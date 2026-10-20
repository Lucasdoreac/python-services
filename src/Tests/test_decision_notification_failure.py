"""Decisão persistida não comprova aceite da notificação pela Cloud Function."""

import pytest
import requests

from Tests.test_change_request import waiting_event, token_active
from Tests.helpers import event_document
from utils.enums import EmailStep


@pytest.fixture
def sender(client, monkeypatch):
    from BLL import send_emails
    monkeypatch.delenv("FLASK_ENV", raising=False)
    return send_emails


def refused_sender(failure):
    def send(payload):
        if failure == "connection":
            raise requests.ConnectionError("synthetic transport failure")
        response = requests.Response()
        response.status_code = 502
        return response
    return send


@pytest.mark.parametrize("path,status", [
    ("approve", "approved_by_reitoria"), ("reject", "rejected_by_reitoria"),
])
@pytest.mark.parametrize("failure", ["http", "connection"])
def test_decision_is_saved_but_failed_notice_is_not_reported_as_success(
    client, monkeypatch, sender, path, status, failure,
):
    event_id, token = waiting_event(client, sender, EmailStep.REITORIA)
    monkeypatch.setattr(sender, "send_email", refused_sender(failure))
    response = client.get(f"/{path}?eventId={event_id}&tokenId={token}&who=reitoria")
    assert response.status_code == 503
    assert response.get_json()["decisionRecorded"] is True
    assert response.get_json()["notificationAccepted"] is False
    assert event_document(event_id)["status"] == status
    assert token_active(token) is False


@pytest.mark.parametrize("failure", ["http", "connection"])
def test_change_request_failure_does_not_claim_the_organizer_was_notified(
    client, monkeypatch, sender, failure,
):
    event_id, token = waiting_event(client, sender)
    monkeypatch.setattr(sender, "send_email", refused_sender(failure))
    response = client.post("/store_changes", data={
        "eventId": event_id, "tokenId": token, "mudancas": "Rever a sala",
    })
    assert response.status_code == 503
    assert response.get_json()["decisionRecorded"] is True
    assert response.get_json()["notificationAccepted"] is False
    assert event_document(event_id)["status"] == "requested_change"
    assert token_active(token) is False


@pytest.mark.parametrize("organizer_status,rector_status,expected", [
    (502, 200, 503), (200, 502, 503), (200, 200, 200),
])
def test_coordination_forwarding_and_organizer_notice_are_checked_separately(
    client, monkeypatch, sender, organizer_status, rector_status, expected,
):
    event_id, token = waiting_event(client, sender)
    organizer = requests.Response()
    organizer.status_code = organizer_status
    rector = requests.Response()
    rector.status_code = rector_status
    forwarded = []
    monkeypatch.setattr(sender, "send_email", lambda payload: organizer)
    monkeypatch.setattr("SLL.administration_approval.send_to_reitoria",
                        lambda event: forwarded.append(event) or rector)
    response = client.get(f"/approve?eventId={event_id}&tokenId={token}&who=coordenacao")
    assert response.status_code == expected
    assert forwarded == [event_id]
    assert event_document(event_id)["status"] == "approved_by_coordenacao"
    assert token_active(token) is False
