"""Contract tests for the authenticated Brevo email endpoint."""

from unittest.mock import Mock

import pytest
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory
from SLL import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    monkeypatch.setattr(MongoDBConnectionFactory, "_client", MongoClient())
    monkeypatch.setattr(MongoDBConnectionFactory, "_database", "api_email_test")
    app = create_app(get_config())
    return app.test_client()


def test_send_email_rejects_missing_internal_api_key(client, monkeypatch):
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "service-key")

    response = client.post(
        "/send-email",
        json={"to": ["user@example.test"], "subject": "Test", "content": "Hello"},
    )

    assert response.status_code == 401


def test_send_email_dry_run_does_not_contact_brevo(client, monkeypatch):
    post = Mock(side_effect=AssertionError("dry-run contacted Brevo"))
    monkeypatch.setattr("SLL.email_routes.requests.post", post)
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "service-key")
    monkeypatch.setenv("EMAIL_DRY_RUN", "true")

    response = client.post(
        "/send-email",
        headers={"X-API-Key": "service-key"},
        json={"to": ["user@example.test"], "subject": "Test", "content": "Hello"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "sent", "dry_run": True}
    post.assert_not_called()


def test_send_email_posts_to_brevo_with_configured_sender(client, monkeypatch):
    post = Mock(return_value=Mock(
        status_code=201,
        content=b'{"messageId":"<accepted@example.test>"}',
        json=Mock(return_value={"messageId": "<accepted@example.test>"}),
        raise_for_status=Mock(),
    ))
    monkeypatch.setattr("SLL.email_routes.requests.post", post)
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "service-key")
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setenv("BREVO_API_KEY", "brevo-test-key")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "reservas@example.test")
    monkeypatch.setenv("BREVO_SENDER_NAME", "Reservas Test")

    response = client.post(
        "/send-email",
        headers={"X-API-Key": "service-key"},
        json={
            "to": "user@example.test",
            "subject": "Test",
            "content": "<p>Hello</p>",
            "is_html": True,
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "sent",
        "messageId": "<accepted@example.test>",
    }
    post.assert_called_once_with(
        "https://api.brevo.com/v3/smtp/email",
        json={
            "sender": {"name": "Reservas Test", "email": "reservas@example.test"},
            "to": [{"email": "user@example.test"}],
            "subject": "Test",
            "htmlContent": "<p>Hello</p>",
        },
        headers={"api-key": "brevo-test-key", "accept": "application/json"},
        timeout=15,
    )


def test_send_email_fails_closed_when_brevo_is_not_configured(client, monkeypatch):
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "service-key")
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_SENDER_EMAIL", raising=False)

    response = client.post(
        "/send-email",
        headers={"X-API-Key": "service-key"},
        json={"to": ["user@example.test"], "subject": "Test", "content": "Hello"},
    )

    assert response.status_code == 503
    assert response.get_json() == {"error": "Email delivery is not configured"}
