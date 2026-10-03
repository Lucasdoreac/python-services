"""Contract tests for the authenticated email endpoint (Brevo and SMTP fallback)."""

import logging
import smtplib
from unittest.mock import Mock

import pytest
import requests
from mongomock import MongoClient
from urllib3.exceptions import ProtocolError

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


BREVO_ENV = {"BREVO_API_KEY": "brevo-test-key", "BREVO_SENDER_EMAIL": "reservas@example.test"}
SMTP_ENV = {
    "SMTP_HOST": "smtp.example.test",
    "SMTP_USER": "sender@example.test",
    "SMTP_PASSWORD": "app-password-secret",
}
PAYLOAD = {
    "to": ["user@example.test"],
    "subject": "Autorização de Acesso",
    "content": '<p>Olá</p><a href="https://app.example.test/auth/callback?email=u&hash=h">Entrar</a>',
    "is_html": True,
}


class FakeSMTP:
    """Records the SMTP conversation instead of opening a socket."""

    instances = []
    fail_login_with = None

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.timeout, self.context = host, port, timeout, context
        self.calls, self.sent = [], []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        if FakeSMTP.fail_login_with:
            raise FakeSMTP.fail_login_with
        self.calls.append(("login", user, password))

    refused = {}

    def send_message(self, message, to_addrs=None):
        self.sent.append((message, to_addrs))
        return dict(FakeSMTP.refused)


class FakeSMTPSSL(FakeSMTP):
    implicit_tls = True


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.instances, FakeSMTP.fail_login_with, FakeSMTP.refused = [], None, {}
    monkeypatch.setattr("SLL.email_routes.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("SLL.email_routes.smtplib.SMTP_SSL", FakeSMTPSSL)
    return FakeSMTP


def enable_email(monkeypatch, **env):
    """Delivery on, every provider variable cleared, then only ``env`` applied."""
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "service-key")
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    for name in (
        "BREVO_API_KEY", "BREVO_SENDER_EMAIL", "EMAIL_PROVIDER", "SMTP_HOST", "SMTP_PORT",
        "SMTP_USER", "SMTP_PASSWORD", "SMTP_SENDER_EMAIL", "SMTP_SENDER_NAME", "SMTP_STARTTLS",
        "FLASK_ENV",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)


def send(client, **overrides):
    return client.post(
        "/send-email", headers={"X-API-Key": "service-key"}, json={**PAYLOAD, **overrides}
    )


def brevo_ok():
    return Mock(return_value=Mock(
        status_code=201, content=b"{}", json=Mock(return_value={"messageId": "<m@x>"}),
        raise_for_status=Mock(),
    ))


def test_smtp_provider_sends_over_starttls_without_contacting_brevo(client, monkeypatch, smtp):
    post = Mock(side_effect=AssertionError("EMAIL_PROVIDER=smtp contacted Brevo"))
    monkeypatch.setattr("SLL.email_routes.requests.post", post)
    enable_email(monkeypatch, EMAIL_PROVIDER="smtp", **BREVO_ENV, **SMTP_ENV)

    response = send(client)

    assert response.status_code == 200
    assert response.get_json() == {"status": "sent", "provider": "smtp"}
    (session,) = smtp.instances
    assert (session.host, session.port) == ("smtp.example.test", 587)
    assert session.calls == ["starttls", ("login", "sender@example.test", "app-password-secret")]
    message, to_addrs = session.sent[0]
    assert to_addrs == ["user@example.test"]
    assert message["From"] == "Reservas UDF <sender@example.test>"
    assert message["To"] == "user@example.test"
    assert message["Subject"] == "Autorização de Acesso"
    assert message.get_content_type() == "text/html"
    assert "hash=h" in message.get_content()  # the magic link survives intact
    message.as_bytes()  # non-ASCII subject/body must be encodable
    post.assert_not_called()


def test_smtp_is_the_fallback_when_brevo_is_not_configured(client, monkeypatch, smtp):
    enable_email(monkeypatch, **SMTP_ENV)

    response = send(client)

    assert response.status_code == 200
    assert response.get_json()["provider"] == "smtp"


def test_smtp_is_the_fallback_when_brevo_request_fails(client, monkeypatch, smtp):
    post = Mock(side_effect=requests.ConnectionError("brevo unreachable"))
    monkeypatch.setattr("SLL.email_routes.requests.post", post)
    enable_email(monkeypatch, **BREVO_ENV, **SMTP_ENV)

    response = send(client)

    assert response.status_code == 200
    assert response.get_json() == {"status": "sent", "provider": "smtp"}
    post.assert_called_once()


def test_brevo_success_does_not_touch_smtp(client, monkeypatch, smtp):
    monkeypatch.setattr("SLL.email_routes.requests.post", brevo_ok())
    enable_email(monkeypatch, **BREVO_ENV, **SMTP_ENV)

    response = send(client)

    assert response.get_json() == {"status": "sent", "messageId": "<m@x>"}
    assert smtp.instances == []


def test_dry_run_does_not_open_an_smtp_connection(client, monkeypatch, smtp):
    enable_email(monkeypatch, **SMTP_ENV)
    monkeypatch.setenv("EMAIL_DRY_RUN", "true")

    response = send(client)

    assert response.get_json() == {"status": "sent", "dry_run": True}
    assert smtp.instances == []


def test_all_providers_failing_returns_502_without_leaking_the_password(
    client, monkeypatch, smtp, caplog
):
    monkeypatch.setattr(
        "SLL.email_routes.requests.post", Mock(side_effect=requests.ConnectionError("down"))
    )
    smtp.fail_login_with = smtplib.SMTPAuthenticationError(535, b"bad credentials")
    enable_email(monkeypatch, **BREVO_ENV, **SMTP_ENV)

    with caplog.at_level(logging.INFO):
        response = send(client)

    assert response.status_code == 502
    assert response.get_json() == {"error": "Email provider request failed"}
    assert "app-password-secret" not in caplog.text
    assert "app-password-secret" not in response.get_data(as_text=True)
    assert "SMTPAuthenticationError" in caplog.text


def test_smtp_provider_without_credentials_fails_closed(client, monkeypatch, smtp):
    enable_email(monkeypatch, EMAIL_PROVIDER="smtp", SMTP_HOST="smtp.example.test")

    response = send(client)

    assert response.status_code == 503
    assert response.get_json() == {"error": "Email delivery is not configured"}
    assert smtp.instances == []


def test_smtp_port_465_uses_implicit_tls_and_skips_starttls(client, monkeypatch, smtp):
    enable_email(monkeypatch, SMTP_PORT="465", **SMTP_ENV)

    response = send(client)

    assert response.status_code == 200
    (session,) = smtp.instances
    assert session.implicit_tls is True
    assert "starttls" not in session.calls


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "mailpit"])
def test_smtp_starttls_can_be_disabled_only_for_a_local_sink_in_development(
    client, monkeypatch, smtp, host
):
    enable_email(
        monkeypatch, SMTP_PORT="1025", SMTP_STARTTLS="false", FLASK_ENV="development",
        **{**SMTP_ENV, "SMTP_HOST": host},
    )

    response = send(client)

    assert response.status_code == 200
    (session,) = smtp.instances
    assert session.port == 1025
    assert "starttls" not in session.calls


@pytest.mark.parametrize(
    "env",
    [
        {"SMTP_HOST": "smtp.example.test", "FLASK_ENV": "development"},  # external host
        {"SMTP_HOST": "localhost", "FLASK_ENV": "production"},  # not development
        {"SMTP_HOST": "mailpit"},  # FLASK_ENV unset
        {"SMTP_HOST": "10.0.0.5", "FLASK_ENV": "development"},  # private, not loopback
    ],
)
def test_smtp_without_tls_is_refused_and_never_sends_credentials(client, monkeypatch, smtp, caplog, env):
    enable_email(
        monkeypatch, SMTP_PORT="587", SMTP_STARTTLS="false", **{**SMTP_ENV, **env}
    )

    with caplog.at_level(logging.INFO):
        response = send(client)

    assert response.status_code == 503
    assert smtp.instances == []  # no connection, hence no login or message in clear text
    assert "app-password-secret" not in caplog.text


def test_smtp_port_465_ignores_starttls_false_and_stays_on_implicit_tls(client, monkeypatch, smtp):
    enable_email(
        monkeypatch, SMTP_PORT="465", SMTP_STARTTLS="false",
        **{**SMTP_ENV, "SMTP_HOST": "smtp.example.test"},
    )

    response = send(client)

    assert response.status_code == 200
    assert smtp.instances[0].implicit_tls is True


def test_smtp_partial_refusal_is_reported_as_partial_not_sent(client, monkeypatch, smtp):
    smtp.refused = {"bad@example.test": (550, b"no such user")}
    enable_email(monkeypatch, EMAIL_PROVIDER="smtp", **SMTP_ENV)

    response = send(client, to=["user@example.test", "bad@example.test"])

    assert response.status_code == 200
    assert response.get_json() == {"status": "partial", "provider": "smtp", "refused": 1}


def test_smtp_all_recipients_refused_is_a_failure(client, monkeypatch, smtp):
    def refuse_all(self, message, to_addrs=None):
        raise smtplib.SMTPRecipientsRefused({"user@example.test": (550, b"no")})

    monkeypatch.setattr(FakeSMTP, "send_message", refuse_all)
    enable_email(monkeypatch, EMAIL_PROVIDER="smtp", **SMTP_ENV)

    response = send(client)

    assert response.status_code == 502


@pytest.mark.parametrize(
    "failure",
    [
        requests.ReadTimeout("read timed out"),
        requests.ConnectionError(ProtocolError("Connection aborted.", ConnectionResetError())),
    ],
)
def test_ambiguous_brevo_failure_does_not_fall_back_to_smtp(client, monkeypatch, smtp, caplog, failure):
    post = Mock(side_effect=failure)
    monkeypatch.setattr("SLL.email_routes.requests.post", post)
    enable_email(monkeypatch, **BREVO_ENV, **SMTP_ENV)

    with caplog.at_level(logging.INFO):
        response = send(client)

    assert response.status_code == 502
    assert smtp.instances == []
    assert type(failure).__name__ in caplog.text


@pytest.mark.parametrize("status", [400, 500, 503])
def test_brevo_http_error_response_falls_back_to_smtp(client, monkeypatch, smtp, status):
    error_response = Mock(status_code=status)
    post = Mock(return_value=Mock(
        raise_for_status=Mock(side_effect=requests.HTTPError(response=error_response))
    ))
    monkeypatch.setattr("SLL.email_routes.requests.post", post)
    enable_email(monkeypatch, **BREVO_ENV, **SMTP_ENV)

    response = send(client)

    assert response.get_json() == {"status": "sent", "provider": "smtp"}


def test_brevo_connect_timeout_falls_back_to_smtp(client, monkeypatch, smtp):
    monkeypatch.setattr(
        "SLL.email_routes.requests.post", Mock(side_effect=requests.ConnectTimeout("connect"))
    )
    enable_email(monkeypatch, **BREVO_ENV, **SMTP_ENV)

    assert send(client).get_json() == {"status": "sent", "provider": "smtp"}


def test_smtp_sender_defaults_to_the_login_and_can_be_overridden(client, monkeypatch, smtp):
    enable_email(
        monkeypatch, SMTP_SENDER_EMAIL="noreply@example.test", SMTP_SENDER_NAME="Reservas", **SMTP_ENV
    )

    send(client)

    assert smtp.instances[0].sent[0][0]["From"] == "Reservas <noreply@example.test>"


def test_smtp_rejects_header_injection_in_the_subject(client, monkeypatch, smtp):
    enable_email(monkeypatch, EMAIL_PROVIDER="smtp", **SMTP_ENV)

    response = send(client, subject="Hello\r\nBcc: attacker@example.test")

    assert response.status_code == 502
    assert all(not session.sent for session in smtp.instances)


def test_smtp_plain_text_messages_are_sent_as_text(client, monkeypatch, smtp):
    enable_email(monkeypatch, EMAIL_PROVIDER="smtp", **SMTP_ENV)

    send(client, content="Olá, use este link", is_html=False)

    assert smtp.instances[0].sent[0][0].get_content_type() == "text/plain"
