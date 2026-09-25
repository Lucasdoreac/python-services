"""Só a pessoa que criou o evento pode alterá-lo ou enviá-lo para aprovação.

Antes, PUT /events/<id> e POST /events/<id>/submit só exigiam estar logado:
qualquer pessoa com e-mail institucional reescrevia o evento de outra (e virava
a organizadora dele) ou o enviava para aprovação reservando uma sala."""
import itertools

import pytest
from bson import ObjectId
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory

_slots = itertools.count(1)
DONA, OUTRA = "dona@udf.edu.br", "outra@udf.edu.br"


class Ok:
    status_code = 200
    def __bool__(self): return True


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    monkeypatch.setattr('SLL.auth_decorators.requests.get', lambda *a, **k: Ok())  # qualquer token vale
    from SLL import create_app
    app = create_app(get_config())
    monkeypatch.setattr('SLL.events_routes.pdf.generate_event_pdf', lambda **kw: None)
    monkeypatch.setattr('SLL.events_routes.send_to_coordenacao', lambda **kw: None)
    monkeypatch.setattr('SLL.events_routes.send_reservation_info_to_reitoria', lambda **kw: None)
    with app.app_context():
        yield app.test_client()


def h(email):
    return {"email": email, "token": "t"}


EVENTO = {"tituloEvento": "Palestra", "classificacao": "lecture", "odsId": "1",
          "descricaoEvento": "d", "status": "draft"}


def rascunho(client):
    return client.post('/events', json=EVENTO, headers=h(DONA)).get_json()["eventId"]


def evento(event_id):
    return MongoDBConnectionFactory.get_db().events.find_one({"_id": ObjectId(event_id)})


def test_other_user_cannot_overwrite_the_event(client):
    event_id = rascunho(client)
    res = client.put(f'/events/{event_id}', json={**EVENTO, "tituloEvento": "sequestrado"}, headers=h(OUTRA))
    assert res.status_code == 403
    doc = evento(event_id)
    assert doc["name"] == "Palestra"  # o título fica em "name" no banco
    assert doc["organizer"]["email"] == DONA


def test_other_user_cannot_submit_the_event(client):
    event_id = rascunho(client)
    n = next(_slots)
    res = client.post(f'/events/{event_id}/submit', headers=h(OUTRA),
                      json={**EVENTO, "roomId": f"sala-dono-{n}", "reservationDate": f"2031-05-{n:02d}T10:00:00.000Z"})
    assert res.status_code == 403
    assert evento(event_id)["status"] == "draft"
    assert list(MongoDBConnectionFactory.get_db().reservations.find({"eventId": event_id})) == []


def test_owner_still_updates_and_submits(client):
    event_id = rascunho(client)
    assert client.put(f'/events/{event_id}', json={**EVENTO, "tituloEvento": "novo"}, headers=h(DONA)).status_code == 200
    n = next(_slots)
    res = client.post(f'/events/{event_id}/submit', headers=h(DONA),
                      json={**EVENTO, "roomId": f"sala-dono-{n}", "reservationDate": f"2031-05-{n:02d}T10:00:00.000Z"})
    assert res.status_code == 200


def test_unknown_event_is_404(client):
    assert client.put('/events/64b000000000000000000000', json=EVENTO, headers=h(DONA)).status_code == 404


def test_other_user_cannot_reserve_a_room_for_the_event(client):
    # Rota antiga (o front usa /submit desde o #64), mas continua no ar.
    event_id = rascunho(client)
    n = next(_slots)
    slot = {"eventId": event_id, "roomId": f"sala-dono-{n}", "reservationDate": f"2031-06-{n:02d}T10:00:00.000Z"}
    assert client.post('/reservations', json=slot, headers=h(OUTRA)).status_code == 403
    assert list(MongoDBConnectionFactory.get_db().reservations.find({"eventId": event_id})) == []
    assert client.post('/reservations', json=slot, headers=h(DONA)).status_code == 201
