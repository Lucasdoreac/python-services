"""Pedido de alterações da Coordenação (PR #63, issue #35) e os pedidos de revisão do PR."""

from pathlib import Path

import pytest
from bson import ObjectId

from DAL import MongoDBConnectionFactory
from Tests.helpers import OWNER, create_draft, event_document, headers, reservations, slot
from utils.enums import EmailStep


@pytest.fixture
def send_emails(client):
    from BLL import send_emails as module

    return module


def waiting_event(client, send_emails, step=EmailStep.COORDENACAO):
    """Evento submetido (com reserva) aguardando a etapa dada, e um token dessa etapa."""
    event_id = create_draft(client)
    chosen = slot()
    assert client.post("/reservations", json={**chosen, "eventId": event_id}, headers=headers(OWNER)).status_code == 201
    status = "waiting" if step == EmailStep.COORDENACAO else "approved_by_coordenacao"
    db = MongoDBConnectionFactory.get_db()
    db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": status}})
    db.reservations.update_many({"eventId": event_id}, {"$set": {"status": status}})
    return event_id, send_emails.create_send_email_token(event_id, step)


def token_active(token_id):
    return MongoDBConnectionFactory.get_db().send_email.find_one({"tokenId": token_id})["active"]


def store(client, event_id, token_id, message="Trocar a sala"):
    return client.post("/store_changes", data={"eventId": event_id, "tokenId": token_id, "mudancas": message})


@pytest.fixture
def production(monkeypatch):
    """Fora de desenvolvimento: o e-mail ao organizador sai pela Cloud Function (simulada)."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("REACT_APP", "reservas.example.com")


@pytest.fixture
def sent(monkeypatch, send_emails):
    calls = []

    class Accepted:
        status_code = 200

    monkeypatch.setattr(send_emails, "send_email", lambda payload: calls.append(payload) or Accepted())
    return calls


def test_the_link_shows_the_form_and_changes_nothing(client, send_emails):
    event_id, token_id = waiting_event(client, send_emails)

    response = client.get(f"/request_changes?eventId={event_id}&tokenId={token_id}")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Requisitar edição" in page
    assert 'name="mudancas"' in page and f'value="{event_id}"' in page and f'value="{token_id}"' in page
    assert event_document(event_id)["status"] == "waiting"
    assert token_active(token_id) is True


def test_only_the_coordination_can_open_the_form(client, send_emails):
    event_id, token_id = waiting_event(client, send_emails, step=EmailStep.REITORIA)

    assert client.get(f"/request_changes?eventId={event_id}&tokenId={token_id}").status_code == 404
    assert store(client, event_id, token_id).status_code == 404
    assert event_document(event_id)["status"] == "approved_by_coordenacao"
    assert token_active(token_id) is True


def test_storing_the_changes_records_the_reason_and_warns_the_organizer(client, send_emails, production, sent):
    event_id, token_id = waiting_event(client, send_emails)

    response = store(client, event_id, token_id, "Trocar a sala <script>x</script>")

    assert response.status_code == 200
    event = event_document(event_id)
    assert event["status"] == "requested_change"
    assert event["changeRequest"]["message"] == "Trocar a sala <script>x</script>"
    assert event["changeRequest"]["by"] == "coordenacao"
    assert [r["status"] for r in reservations(event_id)] == ["requested_change"]  # a sala continua reservada
    assert token_active(token_id) is False
    assert len(sent) == 1 and sent[0]["to"] == [OWNER]
    notice = sent[0]["content"]
    assert "Trocar a sala &lt;script&gt;x&lt;/script&gt;" in notice and "<script>" not in notice
    assert f"https://reservas.example.com/event/type-selection?eventId={event_id}" in notice


def test_the_link_cannot_be_used_twice(client, send_emails, production, sent):
    event_id, token_id = waiting_event(client, send_emails)
    assert store(client, event_id, token_id).status_code == 200

    assert store(client, event_id, token_id, "outra").status_code == 404
    assert event_document(event_id)["changeRequest"]["message"] == "Trocar a sala"
    assert len(sent) == 1


def test_a_token_of_another_event_is_refused(client, send_emails, production, sent):
    event_a, token_a = waiting_event(client, send_emails)
    event_b, _ = waiting_event(client, send_emails)

    assert store(client, event_b, token_a).status_code == 404
    assert event_document(event_b)["status"] == "waiting"
    assert token_active(token_a) is True
    assert sent == []


@pytest.mark.parametrize("message", ["", "   ", "x" * 1001])
def test_an_invalid_reason_reopens_the_form_without_spending_the_token(client, send_emails, production, sent, message):
    event_id, token_id = waiting_event(client, send_emails)

    response = store(client, event_id, token_id, message)

    assert response.status_code == 400
    assert "A justificativa deve ter" in response.get_data(as_text=True)
    assert token_active(token_id) is True
    assert event_document(event_id)["status"] == "waiting"
    assert sent == []
    assert store(client, event_id, token_id, "agora sim").status_code == 200


@pytest.mark.parametrize("failure", ["exception", "http-500"])
def test_a_failed_notice_does_not_undo_the_recorded_request(client, send_emails, production, monkeypatch, failure):
    event_id, token_id = waiting_event(client, send_emails)

    class Failed:
        status_code = 500

    def send(payload):
        if failure == "exception":
            raise ConnectionError("cloud function unreachable")
        return Failed()

    monkeypatch.setattr(send_emails, "send_email", send)

    response = store(client, event_id, token_id)
    assert response.status_code == 503
    assert response.get_json()["decisionRecorded"] is True
    assert event_document(event_id)["status"] == "requested_change"


def test_the_coordination_email_carries_the_request_changes_link_and_the_reitoria_one_does_not(
    client, send_emails, monkeypatch
):
    event_id, _ = waiting_event(client, send_emails)
    monkeypatch.setattr(send_emails.FlowController, "find_event_by_event_id",
                        lambda _id: {"graduationId": "course-1"})
    monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda _id: "teacher-1")
    monkeypatch.setattr(send_emails, "find_teacher_email_by_id", lambda _id: "coord@example.test")
    monkeypatch.setenv("FLASK_ENV", "development")

    coordination = send_emails.send_to_coordenacao(event_id)
    db = MongoDBConnectionFactory.get_db()
    db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": "approved_by_coordenacao"}})
    rector = send_emails.send_to_reitoria(event_id)

    assert "/request_changes?" in coordination
    assert "/request_changes" not in rector


def test_template_file_names_have_no_special_characters():
    folder = Path(__file__).parents[1] / "templates" / "email"
    names = [path.name for path in folder.rglob("*") if path.is_file()]
    assert names and all(name.isascii() for name in names)
