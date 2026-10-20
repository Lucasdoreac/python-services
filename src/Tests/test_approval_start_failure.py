"""Se o aviso de aprovação não é aceito pelo serviço de e-mail, o envio é desfeito e a resposta é 503.

Antes: só uma exceção era tratada (e apenas registrada em log); uma resposta HTTP 4xx/5xx
da Cloud Function era ignorada, o evento ficava em `waiting` e a API respondia sucesso
sem que ninguém tivesse sido avisado.
"""

import pytest
import requests

from DAL import MongoDBConnectionFactory
from Tests.helpers import EVENT, OWNER, create_draft, event_document, headers, reservations, slot


def http_response(status):
    response = requests.Response()
    response.status_code = status
    return response


def sender_returning(monkeypatch, name, result):
    calls = []

    def sender(**kwargs):
        calls.append(kwargs)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(f"SLL.events_routes.{name}", sender)
    return calls


SENDERS = [("lecture", "send_to_coordenacao"), ("class", "send_reservation_info_to_reitoria")]


@pytest.mark.parametrize(("classification", "sender"), SENDERS)
@pytest.mark.parametrize("status", [400, 401, 429, 500, 502, 503])
def test_a_non_2xx_answer_from_the_cloud_function_undoes_the_submission(
    client, monkeypatch, classification, sender, status
):
    event_id = create_draft(client)
    sender_returning(monkeypatch, sender, http_response(status))

    response = client.post(
        f"/events/{event_id}/submit", json={**EVENT, "classificacao": classification, **slot()},
        headers=headers(OWNER),
    )

    assert response.status_code == 503
    assert event_document(event_id)["status"] == "draft"
    assert reservations(event_id) == []


@pytest.mark.parametrize(("classification", "sender"), SENDERS)
def test_the_exception_path_ends_the_same_way(client, monkeypatch, classification, sender):
    event_id = create_draft(client)
    sender_returning(monkeypatch, sender, ValueError("recipient unavailable"))

    response = client.post(
        f"/events/{event_id}/submit", json={**EVENT, "classificacao": classification, **slot()},
        headers=headers(OWNER),
    )

    assert response.status_code == 503
    assert event_document(event_id)["status"] == "draft"
    assert reservations(event_id) == []


@pytest.mark.parametrize(("classification", "sender"), SENDERS)
@pytest.mark.parametrize("status", [200, 201, 202, 204])
def test_a_2xx_answer_keeps_the_submission(client, monkeypatch, classification, sender, status):
    event_id = create_draft(client)
    calls = sender_returning(monkeypatch, sender, http_response(status))

    response = client.post(
        f"/events/{event_id}/submit", json={**EVENT, "classificacao": classification, **slot()},
        headers=headers(OWNER),
    )

    assert response.status_code == 200, response.get_json()
    assert len(calls) == 1
    assert event_document(event_id)["status"] == ("waiting" if classification == "lecture" else "direct_approval")
    assert len(reservations(event_id)) == 1


def test_the_current_spa_flow_gets_503_and_can_retry_without_losing_the_room(client, monkeypatch):
    """POST /reservations + PUT /events: a falha do e-mail volta o evento a rascunho e a SPA tenta de novo."""
    event_id = create_draft(client)
    chosen = slot()
    assert client.post("/reservations", json={**chosen, "eventId": event_id}, headers=headers(OWNER)).status_code == 201
    sender_returning(monkeypatch, "send_to_coordenacao", http_response(502))

    failed = client.put(f"/events/{event_id}", json={**EVENT, "eventId": event_id, "status": "requested", "classificacao": "lecture"},
                        headers=headers(OWNER))

    assert failed.status_code == 503
    assert event_document(event_id)["status"] == "draft"
    assert [r["status"] for r in reservations(event_id)] == ["draft"]

    sender_returning(monkeypatch, "send_to_coordenacao", http_response(200))
    assert client.post("/reservations", json={**chosen, "eventId": event_id}, headers=headers(OWNER)).status_code == 201
    retried = client.put(f"/events/{event_id}", json={**EVENT, "eventId": event_id, "status": "requested", "classificacao": "lecture"},
                         headers=headers(OWNER))
    assert retried.status_code == 200
    assert event_document(event_id)["status"] == "waiting"
    assert len(reservations(event_id)) == 1


def test_a_failed_start_revokes_the_links_that_may_have_been_issued(client, monkeypatch):
    event_id = create_draft(client)
    MongoDBConnectionFactory.get_db().send_email.insert_one(
        {"tokenId": "t", "eventId": event_id, "step": 0, "active": True}
    )
    sender_returning(monkeypatch, "send_to_coordenacao", http_response(500))

    client.post(f"/events/{event_id}/submit", json={**EVENT, "classificacao": "lecture", **slot()},
                headers=headers(OWNER))

    assert MongoDBConnectionFactory.get_db().send_email.find_one({"tokenId": "t"})["active"] is False


def test_a_busy_room_lock_answers_503_and_writes_nothing(client, monkeypatch):
    """O lock da sala não tem alternativa silenciosa: sem o lock, nada é reservado."""
    from datetime import datetime, timedelta, timezone

    from DAL.reservation_manager import ReservationManager

    event_id = create_draft(client)
    chosen = slot()
    MongoDBConnectionFactory.get_db().reservation_locks.insert_one({
        "_id": f"room:{chosen['roomId']}", "owner": "another-process",
        "leaseExpiresAt": datetime.now(timezone.utc) + timedelta(minutes=5),
    })
    monkeypatch.setattr(ReservationManager, "_LOCK_WAIT_SECONDS", 0)

    response = client.post(f"/events/{event_id}/submit", json={**EVENT, **chosen}, headers=headers(OWNER))

    assert response.status_code == 503
    assert reservations(event_id) == []
    assert event_document(event_id)["status"] == "draft"

    via_spa_route = client.post("/reservations", json={**chosen, "eventId": event_id}, headers=headers(OWNER))
    assert via_spa_route.status_code == 503
    assert reservations(event_id) == []
