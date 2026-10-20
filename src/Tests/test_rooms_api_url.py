from mongomock import MongoClient

import configmodule
from SLL import create_app


def test_room_schedule_uses_canonical_rest_paths(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr(configmodule.Config, "MONGO_URI", "mongodb://localhost")
    monkeypatch.setattr(configmodule.Config, "MONGO_DATABASE", "test_db")
    app = create_app(configmodule.get_config())
    requested_urls = []

    class Response:
        status_code = 200

        def __init__(self, url):
            self.url = url

        def json(self):
            if self.url.split("?", maxsplit=1)[0].endswith("/campus/"):
                return []
            if "room_id=" in self.url:
                return {"id": "room-1"}
            if "campus_id=" in self.url:
                return {"id": "campus-1"}
            return {"data": [], "pagination": {"total_pages": 0}}

    def request(url, *args):
        requested_urls.append(url)
        return Response(url)

    monkeypatch.setenv("URL_restapi", "http://internal:5081/restapi")
    monkeypatch.setattr(
        "SLL.cluster_api.request_methods.RestApiRequestMethods.get_request_with_params",
        request,
    )
    monkeypatch.setattr(
        "SLL.cluster_api.request_methods.RestApiRequestMethods.get_request_simple",
        request,
    )

    from BLL.index import FlowController

    with app.app_context():
        FlowController().filter_available_rooms(
            "2026-09-27", "08:00:00", page=1, page_size=10
        )
        FlowController.find_room_by_id("room-1")
        FlowController.find_campus_by_id("campus-1")

    assert requested_urls == [
        "http://internal:5081/restapi/rooms/",
        "http://internal:5081/restapi/campus/",
        "http://internal:5081/restapi/rooms/?room_id=room-1",
        "http://internal:5081/restapi/campus/?campus_id=campus-1",
    ]
