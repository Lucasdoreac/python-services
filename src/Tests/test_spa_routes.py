"""Rotas que a SPA vigente (interfaces-usuario, bc9c63d) chama não podem desaparecer da API.

A lista vem de `reservas/src/services/client.js` e das páginas que o usam; a SPA
da consolidação acrescenta /auth/exchange, /auth/logout e /events/<id>/submit,
que dependem de outros repositórios e entram só quando existirem lá.
"""

import pytest

from Tests.helpers import EVENT, OWNER, create_draft, event_document, headers, reservations, slot

CONSUMED_BY_THE_SPA = [
    ("/auth/send-link", "POST"),
    ("/auth/validate", "GET"),
    ("/courses", "GET"),
    ("/types", "GET"),
    ("/events", "GET"),
    ("/events", "POST"),
    ("/events/<string:event_id>", "PUT"),
    ("/reservations", "GET"),
    ("/reservations", "POST"),
    ("/rooms", "GET"),
    ("/rooms/available-rooms", "GET"),
]


@pytest.mark.parametrize(("rule", "method"), CONSUMED_BY_THE_SPA)
def test_the_route_the_spa_calls_still_exists(client, rule, method):
    from flask import current_app

    registered = {(r.rule, m) for r in current_app.url_map.iter_rules() for m in r.methods}
    assert (rule, method) in registered


def test_the_current_spa_flow_reserves_then_submits_the_event(client):
    """POST /events -> POST /reservations -> PUT /events/<id> com status requested."""
    event_id = create_draft(client)
    chosen = slot()

    created = client.post("/reservations", json={**chosen, "eventId": event_id}, headers=headers(OWNER))
    assert created.status_code == 201, created.get_json()

    submitted = client.put(
        f"/events/{event_id}", json={**EVENT, "eventId": event_id, "status": "requested", "classificacao": "lecture"},
        headers=headers(OWNER),
    )
    assert submitted.status_code == 200, submitted.get_json()
    assert event_document(event_id)["status"] == "waiting"
    assert [r["status"] for r in reservations(event_id)] == ["waiting"]
    listed = client.get(f"/reservations?eventId={event_id}", headers=headers(OWNER))
    assert listed.status_code == 200


def test_repeating_the_reservation_of_the_same_event_is_idempotent(client):
    event_id = create_draft(client)
    chosen = slot()
    body = {**chosen, "eventId": event_id}

    assert client.post("/reservations", json=body, headers=headers(OWNER)).status_code == 201
    assert client.post("/reservations", json=body, headers=headers(OWNER)).status_code == 201
    assert len(reservations(event_id)) == 1

    other_event = create_draft(client)
    clash = client.post("/reservations", json={**chosen, "eventId": other_event}, headers=headers(OWNER))
    assert clash.status_code == 400
    assert reservations(other_event) == []
