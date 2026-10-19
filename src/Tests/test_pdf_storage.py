import pytest
from mongomock import MongoClient

import configmodule
from DAL import MongoDBConnectionFactory
from SLL import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("PDF_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("EMAIL_ASSETS_URL", raising=False)
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    monkeypatch.setattr(configmodule.Config, "MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setattr(configmodule.Config, "MONGO_DATABASE", "labtech_test")
    MongoDBConnectionFactory._client = MongoClient()
    MongoDBConnectionFactory._database = "pdf_storage_test"
    app = create_app(configmodule.get_config())
    yield app


def test_pdf_link_uses_api_without_minio(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.delenv("MINIO_URL", raising=False)
    monkeypatch.setenv("SERVER_SCHEME", "https")
    monkeypatch.setenv("SERVER_NAME", "reservas-api.example.com")

    link = send_emails._pdf_link("event-123")
    assert link.startswith("https://reservas-api.example.com/events/event-123/pdf?exp=")
    assert "&sig=" in link


def test_pdf_link_uses_minio_when_configured(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.setenv("MINIO_URL", "https://objects.example.com/")

    assert send_emails._pdf_link("event-123") == (
        "https://objects.example.com/labtech/reservation-pdfs/event-123.pdf"
    )


def test_pdf_link_uses_public_api_base_before_internal_minio(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.setenv("MINIO_URL", "http://minio:9000")
    monkeypatch.setenv("PDF_PUBLIC_BASE_URL", "http://127.0.0.1:5000/")

    link = send_emails._pdf_link("event-123")

    assert link.startswith("http://127.0.0.1:5000/events/event-123/pdf?exp=")
    assert "&sig=" in link


def test_email_logo_url_reuses_shared_public_email_assets_base(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.setenv(
        "EMAIL_ASSETS_URL",
        "https://reservas-web.example.com/labtech/email-icones/",
    )
    monkeypatch.setenv("PDF_PUBLIC_BASE_URL", "http://127.0.0.1:5000")

    assert send_emails._email_logo_url() == (
        "https://reservas-web.example.com/labtech/email-icones/dw-corp-logo.png"
    )


def test_email_logo_url_reuses_pdf_public_base_locally(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.delenv("EMAIL_ASSETS_URL", raising=False)
    monkeypatch.setenv("PDF_PUBLIC_BASE_URL", "http://127.0.0.1:5000/")

    assert send_emails._email_logo_url() == (
        "http://127.0.0.1:5000/static/email/dw-corp-logo.png"
    )


def test_email_logo_url_uses_current_api_origin_when_not_configured(monkeypatch, app):
    from BLL import send_emails

    monkeypatch.delenv("EMAIL_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("PDF_PUBLIC_BASE_URL", raising=False)

    with app.test_request_context("/", base_url="https://reservas-api.example.com"):
        assert send_emails._email_logo_url() == (
            "https://reservas-api.example.com/static/email/dw-corp-logo.png"
        )


def test_dw_corp_logo_is_served_by_the_api(app):
    from pathlib import Path

    response = app.test_client().get("/static/email/dw-corp-logo.png")
    logo_path = Path(__file__).parents[1] / "SLL" / "static" / "email" / "dw-corp-logo.png"

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data == logo_path.read_bytes()


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

    from SLL import events_routes, signed_links

    monkeypatch.setattr(events_routes, "ReservationManager", FakeReservationManager)

    response = app.test_client().get(f"/events/event-123/pdf?{signed_links.signed_query('event-123')}")

    assert response.status_code == 200
    assert response.data == b"%PDF-test"
    assert response.mimetype == "application/pdf"
    assert response.headers["Content-Disposition"] == 'inline; filename="event-123.pdf"'


def test_pdf_route_returns_404_when_not_found(monkeypatch, app):
    class FakeReservationManager:
        def get_pdf_by_event_id(self, event_id):
            return None

    from SLL import events_routes, signed_links

    monkeypatch.setattr(events_routes, "ReservationManager", FakeReservationManager)

    response = app.test_client().get(f"/events/missing/pdf?{signed_links.signed_query('missing')}")

    assert response.status_code == 404
    assert response.get_json() == {"error": "PDF not found"}
