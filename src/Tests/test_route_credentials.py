"""Rotas que respondiam sem credenciais agora exigem um usuário autenticado."""

from Tests.helpers import OTHER, OWNER, create_draft, headers


def test_reservations_by_date_needs_a_user_token(client):
    assert client.get("/reservations/2031-03-01").status_code == 401
    assert client.get("/reservations/2031-03-01", headers=headers(OWNER)).status_code in (200, 404)


def test_notify_reservation_needs_a_token_and_the_organizer(client, monkeypatch):
    event_id = create_draft(client)
    assert client.get(f"/notify_reservation?eventId={event_id}").status_code == 401
    assert client.get(f"/notify_reservation?eventId={event_id}", headers=headers(OTHER)).status_code == 403
    assert client.get("/notify_reservation?eventId=000000000000000000000000",
                      headers=headers(OWNER)).status_code == 404
    assert client.get("/notify_reservation?eventId=not-an-object-id", headers=headers(OWNER)).status_code == 404

    calls = []

    class Sent:
        status_code = 200

    monkeypatch.setattr("SLL.administration_approval.send_reservation_info_to_reitoria",
                        lambda event_id: calls.append(event_id) or Sent())
    monkeypatch.delenv("FLASK_ENV", raising=False)
    ok = client.get(f"/notify_reservation?eventId={event_id}", headers=headers(OWNER))
    assert ok.status_code == 200 and calls == [event_id]


def test_notify_reservation_failure_does_not_leak_the_exception(client, monkeypatch):
    event_id = create_draft(client)

    def boom(event_id):
        raise RuntimeError("secret-host.internal refused")

    monkeypatch.setattr("SLL.administration_approval.send_reservation_info_to_reitoria", boom)
    response = client.get(f"/notify_reservation?eventId={event_id}", headers=headers(OWNER))

    assert response.status_code == 500
    assert "secret-host" not in response.get_data(as_text=True)
