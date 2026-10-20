"""Dados e atalhos comuns aos testes de rota (cliente HTTP com Mongo em memória)."""

import itertools
from datetime import date, timedelta

from bson import ObjectId

from DAL import MongoDBConnectionFactory

OWNER = "owner@udf.edu.br"
OTHER = "other@udf.edu.br"
EVENT = {
    "tituloEvento": "Palestra de Extensão",
    "classificacao": "lecture",
    "odsId": "1",
    "descricaoEvento": "Descrição",
    "status": "draft",
}
_slots = itertools.count(1)


def headers(email):
    return {"email": email, "token": "test-token"}


def create_draft(client, owner=OWNER):
    response = client.post("/events", json=EVENT, headers=headers(owner))
    assert response.status_code == 200, response.get_json()
    return response.get_json()["eventId"]


def slot():
    n = next(_slots)
    day = date(2031, 3, 1) + timedelta(days=n)  # um dia distinto por chamada, sempre válido
    return {
        "roomId": f"test-room-{n}",
        "reservationDate": f"{day.isoformat()}T10:00:00.000Z",
    }


def event_document(event_id):
    return MongoDBConnectionFactory.get_db().events.find_one({"_id": ObjectId(event_id)})


def reservations(event_id):
    return list(MongoDBConnectionFactory.get_db().reservations.find({"eventId": event_id}))
