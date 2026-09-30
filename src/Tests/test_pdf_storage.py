import pytest
from mongomock import MongoClient

from configmodule import get_config
from SLL import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DATABASE", "labtech_test")
    app = create_app(get_config())
    yield app


def test_pdf_link_uses_api_without_minio(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.delenv("MINIO_URL", raising=False)
    monkeypatch.setenv("SERVER_SCHEME", "https")
    monkeypatch.setenv("SERVER_NAME", "reservas-api.example.com")

    assert send_emails._pdf_link("event-123") == (
        "https://reservas-api.example.com/events/event-123/pdf"
    )
    assert send_emails._icon_url("pdf.png") == ""


def test_pdf_link_uses_minio_when_configured(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.setenv("MINIO_URL", "https://objects.example.com/")

    assert send_emails._pdf_link("event-123") == (
        "https://objects.example.com/labtech/reservation-pdfs/event-123.pdf"
    )
    assert send_emails._icon_url("pdf.png") == (
        "https://objects.example.com/labtech/email-icones/pdf.png"
    )


def test_save_pdf_persists_bytes_to_mongo_without_minio(monkeypatch, app, tmp_path):
    from BLL import pdf

    monkeypatch.delenv("MINIO_URL", raising=False)
    saved = {}

    class FakeReservationManager:
        def insert_pdf(self, document):
            saved.update(document)

    monkeypatch.setattr(pdf, "ReservationManager", FakeReservationManager)
    pdf_path = tmp_path / "event.pdf"
    pdf_path.write_bytes(b"%PDF-test")

    pdf.save_pdf("event-123", str(pdf_path))

    assert saved["eventId"] == "event-123"
    assert saved["content"] == b"%PDF-test"
    assert saved["contentType"] == "application/pdf"
    assert saved["path"] == "/events/event-123/pdf"


def test_pdf_route_returns_bytes_from_mongo(monkeypatch, app):
    class FakeReservationManager:
        def get_pdf_by_event_id(self, event_id):
            assert event_id == "event-123"
            return {
                "content": b"%PDF-test",
                "filename": "event-123.pdf",
                "contentType": "application/pdf",
            }

    from SLL import events_routes

    monkeypatch.setattr(events_routes, "ReservationManager", FakeReservationManager)

    response = app.test_client().get("/events/event-123/pdf")

    assert response.status_code == 200
    assert response.data == b"%PDF-test"
    assert response.mimetype == "application/pdf"
    assert response.headers["Content-Disposition"] == 'inline; filename="event-123.pdf"'


def test_pdf_route_returns_404_when_not_found(monkeypatch, app):
    class FakeReservationManager:
        def get_pdf_by_event_id(self, event_id):
            return None

    from SLL import events_routes

    monkeypatch.setattr(events_routes, "ReservationManager", FakeReservationManager)

    response = app.test_client().get("/events/missing/pdf")

    assert response.status_code == 404
    assert response.get_json() == {"error": "PDF not found"}
