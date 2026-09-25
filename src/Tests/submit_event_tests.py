"""POST /events/<id>/submit (issue #64): reserva a sala e envia o evento numa
requisição só.

Antes o front fazia POST /reservations e depois PUT /events/<id>. Se o PUT
falhasse, a reserva ficava gravada com o evento em rascunho (sala presa), e
tentar de novo dava 409: a sala estava "ocupada" pela reserva do próprio evento."""
import itertools

import pytest
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory

_slots = itertools.count(1)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    monkeypatch.setattr('SLL.auth_decorators.token_required', lambda f: f)
    from SLL import create_app
    app = create_app(get_config())
    # Sem PDF (MinIO) nem e-mail: o que interessa é o que fica gravado.
    monkeypatch.setattr('SLL.events_routes.pdf.generate_event_pdf', lambda **kw: None)
    monkeypatch.setattr('SLL.events_routes.send_to_coordenacao', lambda **kw: None)
    monkeypatch.setattr('SLL.events_routes.send_reservation_info_to_reitoria', lambda **kw: None)
    with app.app_context():
        yield app.test_client()


def new_draft(client):
    event = {"tituloEvento": "Palestra de Extensão", "classificacao": "lecture",
             "odsId": "1", "descricaoEvento": "d", "status": "draft"}
    res = client.post('/events', json=event, headers={"email": "prof@udf.edu.br"})
    return res.get_json()["eventId"], event


def slot():
    # Horário único por teste: o Mongo em memória é compartilhado pela suíte.
    n = next(_slots)
    return {"roomId": f"sala-submit-{n}", "reservationDate": f"2031-03-{n:02d}T10:00:00.000Z"}


def reservations_of(event_id):
    return list(MongoDBConnectionFactory.get_db().reservations.find({"eventId": event_id}))


def status_of(event_id):
    from bson import ObjectId
    return MongoDBConnectionFactory.get_db().events.find_one({"_id": ObjectId(event_id)})["status"]


def test_submit_reserves_room_and_starts_approval(client):
    event_id, event = new_draft(client)
    res = client.post(f'/events/{event_id}/submit', json={**event, **slot()},
                      headers={"email": "prof@udf.edu.br"})
    assert res.status_code == 200, res.get_json()
    assert len(reservations_of(event_id)) == 1
    assert status_of(event_id) == "waiting"


def test_event_update_failure_leaves_no_orphan_reservation(client, monkeypatch):
    event_id, event = new_draft(client)
    from BLL import FlowController
    from flask import jsonify
    monkeypatch.setattr(FlowController, "update_event",
                        staticmethod(lambda *a, **k: (jsonify({"error": "boom"}), 500)))
    res = client.post(f'/events/{event_id}/submit', json={**event, **slot()},
                      headers={"email": "prof@udf.edu.br"})
    assert res.status_code == 500
    assert reservations_of(event_id) == []
    assert status_of(event_id) == "draft"


def test_retry_with_own_reservation_is_not_a_conflict(client):
    event_id, event = new_draft(client)
    s = slot()
    # Situação que o fluxo antigo deixava: reserva gravada, evento em rascunho.
    assert client.post('/reservations', json={"eventId": event_id, **s}).status_code == 201
    res = client.post(f'/events/{event_id}/submit', json={**event, **s},
                      headers={"email": "prof@udf.edu.br"})
    assert res.status_code == 200, res.get_json()
    assert len(reservations_of(event_id)) == 1
    assert status_of(event_id) == "waiting"


def test_room_taken_by_another_event_is_409_and_event_untouched(client):
    other_id, _ = new_draft(client)
    event_id, event = new_draft(client)
    s = slot()
    assert client.post('/reservations', json={"eventId": other_id, **s}).status_code == 201
    res = client.post(f'/events/{event_id}/submit', json={**event, **s},
                      headers={"email": "prof@udf.edu.br"})
    assert res.status_code == 409
    assert reservations_of(event_id) == []
    assert status_of(event_id) == "draft"


def test_missing_room_is_400(client):
    event_id, event = new_draft(client)
    res = client.post(f'/events/{event_id}/submit', json=event, headers={"email": "prof@udf.edu.br"})
    assert res.status_code == 400
    assert status_of(event_id) == "draft"
