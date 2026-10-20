"""E-mails de aprovação sem ícones do MinIO: botões em texto e logo servido pela API."""

from pathlib import Path

import pytest
from bson import ObjectId

from DAL import MongoDBConnectionFactory
from Tests.helpers import create_draft


@pytest.fixture
def send_emails(client, monkeypatch):
    from BLL import send_emails as module

    monkeypatch.setenv("FLASK_ENV", "development")  # os remetentes devolvem o HTML renderizado
    monkeypatch.setenv("MINIO_URL", "http://minio.test:9000")
    monkeypatch.delenv("EMAIL_ASSETS_URL", raising=False)
    monkeypatch.setattr(module, "get_coordinator_by_graduation_id", lambda _id: "teacher-1")
    monkeypatch.setattr(module, "find_teacher_email_by_id", lambda _id: "coord@example.test")
    return module


def set_status(event_id, status):
    MongoDBConnectionFactory.get_db().events.update_one({"_id": ObjectId(event_id)}, {"$set": {"status": status}})


def test_the_approval_email_has_text_buttons_the_logo_and_the_minio_pdf_link(client, send_emails):
    event_id = create_draft(client)

    html = send_emails.send_to_coordenacao(event_id)

    assert "Aprovar" in html and "Rejeitar" in html and "Solicitar alterações" in html
    assert "email-icones" not in html  # nenhum ícone do MinIO
    assert "/static/email/dw-corp-logo.png" in html
    assert f"http://minio.test:9000/labtech/reservation-pdfs/{event_id}.pdf" in html


def test_the_rector_email_has_no_request_changes_button(client, send_emails):
    event_id = create_draft(client)
    set_status(event_id, "approved_by_coordenacao")

    html = send_emails.send_to_reitoria(event_id)

    assert "Aprovar" in html and "Rejeitar" in html and "Solicitar alterações" not in html


def test_the_status_and_reservation_emails_use_the_logo(client, send_emails):
    event_id = create_draft(client)
    set_status(event_id, "waiting")
    token = send_emails.create_send_email_token(event_id, send_emails.EmailStep.COORDENACAO)

    status_html = send_emails.send_event_status(event_id, True, "coordenacao", token)
    info_html = send_emails.send_reservation_info_to_reitoria(event_id)

    for html in (status_html, info_html):
        assert "dw-corp-logo.png" in html and "email-icones" not in html


def test_the_logo_url_prefers_the_configured_assets_directory(client, send_emails, monkeypatch):
    monkeypatch.setenv("EMAIL_ASSETS_URL", "https://reservas-web.example.com/labtech/email-icones/")

    assert send_emails.email_logo_url() == "https://reservas-web.example.com/labtech/email-icones/dw-corp-logo.png"


def test_the_logo_url_falls_back_to_the_current_api_origin(client, send_emails):
    with client.application.test_request_context("/", base_url="https://reservas-api.example.com"):
        assert send_emails.email_logo_url() == "https://reservas-api.example.com/static/email/dw-corp-logo.png"


def test_the_logo_url_outside_a_request_uses_the_server_settings(client, send_emails, monkeypatch):
    monkeypatch.setenv("SERVER_SCHEME", "https")
    monkeypatch.setenv("SERVER_NAME", "api.example.test")

    assert send_emails.email_logo_url() == "https://api.example.test/static/email/dw-corp-logo.png"


def test_the_api_serves_the_logo(client):
    response = client.get("/static/email/dw-corp-logo.png")
    logo = Path(__file__).parents[1] / "SLL" / "static" / "email" / "dw-corp-logo.png"

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data == logo.read_bytes()
