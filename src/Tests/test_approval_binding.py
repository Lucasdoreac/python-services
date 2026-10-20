"""O token do link de aprovação vale para o evento e a etapa para os quais foi emitido.

Antes: um tokenId inexistente, de outro evento ou da outra etapa passava na verificação
e o status do evento era gravado mesmo assim.
"""

import pytest
from bson import ObjectId

from DAL import MongoDBConnectionFactory
from Tests.helpers import create_draft, event_document
from utils.enums import EmailStep


@pytest.fixture
def send_emails(client):
    from BLL import send_emails as module

    return module


@pytest.fixture(autouse=True)
def development(monkeypatch):
    # Em desenvolvimento nenhum e-mail sai: as rotas devolvem o HTML renderizado.
    monkeypatch.setenv("FLASK_ENV", "development")


def set_status(event_id, status):
    MongoDBConnectionFactory.get_db().events.update_one(
        {"_id": ObjectId(event_id)}, {"$set": {"status": status}}
    )


def token_record(token_id):
    return MongoDBConnectionFactory.get_db().send_email.find_one({"tokenId": token_id})


def waiting_event_with_token(client, send_emails, step=EmailStep.COORDENACAO):
    event_id = create_draft(client)
    set_status(
        event_id,
        "waiting" if step == EmailStep.COORDENACAO else "approved_by_coordenacao",
    )
    return event_id, send_emails.create_send_email_token(event_id, step)


def link(path, event_id, token_id, who="coordenacao"):
    return f"{path}?eventId={event_id}&tokenId={token_id}&who={who}"


def test_a_valid_link_records_the_decision_once(client, send_emails):
    event_id, token_id = waiting_event_with_token(client, send_emails)

    first = client.get(link("/reject", event_id, token_id))
    assert first.status_code == 200
    assert event_document(event_id)["status"] == "rejected_by_coordenacao"
    assert token_record(token_id)["active"] is False

    replay = client.get(link("/reject", event_id, token_id))
    assert replay.status_code == 404


@pytest.mark.parametrize("path", ["/approve", "/reject"])
def test_an_unknown_token_changes_nothing(client, send_emails, path):
    event_id, _ = waiting_event_with_token(client, send_emails)

    response = client.get(link(path, event_id, "token-that-was-never-issued"))

    assert response.status_code == 404
    assert event_document(event_id)["status"] == "waiting"


@pytest.mark.parametrize("path", ["/approve", "/reject"])
def test_a_token_of_another_event_changes_nothing(client, send_emails, path):
    event_a, token_a = waiting_event_with_token(client, send_emails)
    event_b, _ = waiting_event_with_token(client, send_emails)

    response = client.get(link(path, event_b, token_a))

    assert response.status_code == 404
    assert event_document(event_b)["status"] == "waiting"
    assert event_document(event_a)["status"] == "waiting"
    assert token_record(token_a)["active"] is True  # o token do evento A continua válido para o A


@pytest.mark.parametrize("path", ["/approve", "/reject"])
def test_a_coordination_token_cannot_decide_as_the_rector(client, send_emails, path):
    event_id, token_id = waiting_event_with_token(client, send_emails)
    set_status(event_id, "approved_by_coordenacao")

    response = client.get(link(path, event_id, token_id, who="reitoria"))

    assert response.status_code == 404
    assert event_document(event_id)["status"] == "approved_by_coordenacao"
    assert token_record(token_id)["active"] is True


def test_a_rector_token_cannot_decide_as_the_coordination(client, send_emails):
    event_id, token_id = waiting_event_with_token(client, send_emails, step=EmailStep.REITORIA)
    set_status(event_id, "waiting")

    response = client.get(link("/approve", event_id, token_id, who="coordenacao"))

    assert response.status_code == 404
    assert event_document(event_id)["status"] == "waiting"
    assert token_record(token_id)["active"] is True


@pytest.mark.parametrize("who", ["", "admin", "Coordenacao"])
def test_an_unknown_who_is_refused(client, send_emails, who):
    event_id, token_id = waiting_event_with_token(client, send_emails)

    response = client.get(link("/approve", event_id, token_id, who=who))

    assert response.status_code == 404
    assert event_document(event_id)["status"] == "waiting"


def test_a_token_is_refused_when_the_event_is_not_at_its_stage(client, send_emails):
    event_id, token_id = waiting_event_with_token(client, send_emails)
    set_status(event_id, "rejected_by_coordenacao")  # já decidido por outro caminho

    response = client.get(link("/approve", event_id, token_id))

    assert response.status_code == 404
    assert event_document(event_id)["status"] == "rejected_by_coordenacao"


def test_a_new_submission_revokes_the_links_of_the_previous_one(client, send_emails, monkeypatch):
    event_id, old_token = waiting_event_with_token(client, send_emails)
    monkeypatch.setattr(send_emails.FlowController, "find_event_by_event_id",
                        lambda _id: {"graduationId": "course-1"})
    monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda _id: "teacher-1")
    monkeypatch.setattr(send_emails, "find_teacher_email_by_id", lambda _id: "coord@example.test")

    send_emails.send_to_coordenacao(event_id)

    assert token_record(old_token)["active"] is False
    assert client.get(link("/approve", event_id, old_token)).status_code == 404
    assert event_document(event_id)["status"] == "waiting"


def test_the_coordination_recipient_list_does_not_accumulate(client, send_emails, monkeypatch):
    event_id, _ = waiting_event_with_token(client, send_emails)
    monkeypatch.setattr(send_emails.FlowController, "find_event_by_event_id",
                        lambda _id: {"graduationId": "course-1"})
    monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda _id: "teacher-1")
    monkeypatch.setattr(send_emails, "find_teacher_email_by_id", lambda _id: "coord@example.test")
    before = list(send_emails.emails["coordenacao"])

    send_emails.send_to_coordenacao(event_id)
    send_emails.send_to_coordenacao(event_id)

    assert send_emails.emails["coordenacao"] == before


def test_tokens_are_not_derived_from_the_clock(client, send_emails):
    event_id = create_draft(client)
    first = send_emails.create_send_email_token(event_id, EmailStep.COORDENACAO)
    second = send_emails.create_send_email_token(event_id, EmailStep.COORDENACAO)

    assert first != second
    assert len(first) >= 40
