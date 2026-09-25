"""Reserva com data no passado é recusada pela API (400).

Antes só o calendário do front (minDate) impedia; um POST direto em
/reservations ou /events/<id>/submit gravava reserva em data que já passou.

O front manda o horário de Brasília marcado com 'Z' (formatDateForMongoDB
desloca o fuso), então "agora" também é comparado no horário de Brasília."""
import itertools
from datetime import datetime

import pytest
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory

_rooms = itertools.count(1)
PAST = "2020-01-10T10:00:00.000Z"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    monkeypatch.setattr('SLL.auth_decorators.token_required', lambda f: f)
    from SLL import create_app
    app = create_app(get_config())
    monkeypatch.setattr('SLL.events_routes.pdf.generate_event_pdf', lambda **kw: None)
    monkeypatch.setattr('SLL.events_routes.send_to_coordenacao', lambda **kw: None)
    monkeypatch.setattr('SLL.events_routes.send_reservation_info_to_reitoria', lambda **kw: None)
    with app.app_context():
        yield app.test_client()


def reservations_in(room_id):
    return list(MongoDBConnectionFactory.get_db().reservations.find({"roomId": room_id}))


def test_post_reservation_in_the_past_is_rejected(client):
    room = f"sala-passado-{next(_rooms)}"
    res = client.post('/reservations', json={
        "eventId": "66193fb3e764a62988bbcf32", "reservationDate": PAST, "roomId": room})
    assert res.status_code == 400
    assert reservations_in(room) == []


def test_submit_in_the_past_is_rejected_and_event_stays_draft(client):
    event = {"tituloEvento": "Palestra", "classificacao": "lecture",
             "odsId": "1", "descricaoEvento": "d", "status": "draft"}
    event_id = client.post('/events', json=event,
                           headers={"email": "prof@udf.edu.br"}).get_json()["eventId"]
    room = f"sala-passado-{next(_rooms)}"
    res = client.post(f'/events/{event_id}/submit',
                      json={**event, "roomId": room, "reservationDate": PAST},
                      headers={"email": "prof@udf.edu.br"})
    assert res.status_code == 400
    assert reservations_in(room) == []
    from bson import ObjectId
    doc = MongoDBConnectionFactory.get_db().events.find_one({"_id": ObjectId(event_id)})
    assert doc["status"] == "draft"


@pytest.mark.parametrize("start, ok", [
    ("2026-09-25T09:59:00.000Z", False),  # um minuto antes de "agora"
    ("2026-09-25T10:00:00.000Z", True),   # exatamente agora
    ("2026-09-25T18:00:00.000Z", True),   # mais tarde no mesmo dia
])
def test_boundary_uses_brasilia_time(start, ok):
    from BLL.index import parse_reservation_start
    # 13:00 UTC = 10:00 em Brasília
    now_utc = datetime(2026, 9, 25, 13, 0)
    if ok:
        assert parse_reservation_start(start, now_utc=now_utc) == datetime.fromisoformat(start[:-1])
    else:
        with pytest.raises(ValueError, match="passado"):
            parse_reservation_start(start, now_utc=now_utc)
