from Tests.test_event_submission import OWNER, client, headers  # noqa: F401


def test_rooms_without_a_room_id_is_a_400_not_a_500(client):
    response = client.get("/rooms", headers=headers(OWNER))
    assert response.status_code == 400
    assert response.get_json() == {"error": "roomId is required"}


def test_rooms_returns_the_room_for_a_valid_id(client, monkeypatch):
    from BLL.index import FlowController

    monkeypatch.setattr(FlowController, "find_room_by_id", staticmethod(lambda room_id: {"id": room_id, "name": "A1"}))
    response = client.get("/rooms?roomId=room-7", headers=headers(OWNER))
    assert response.status_code == 200 and response.get_json() == {"id": "room-7", "name": "A1"}


def test_rooms_passes_a_lookup_error_through_instead_of_crashing(client, monkeypatch):
    from flask import jsonify

    from BLL.index import FlowController

    monkeypatch.setattr(FlowController, "find_room_by_id",
                        staticmethod(lambda room_id: (jsonify({"error": "An unexpected error occurred"}), 400)))
    response = client.get("/rooms?roomId=missing", headers=headers(OWNER))
    assert response.status_code == 400
