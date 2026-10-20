"""Saída de e-mail: só a Cloud Function (CLOUD_FUNCTION_URL); allowlist de homologação opcional."""

from unittest.mock import Mock

import pytest

from SLL import email_service

ALLOWED = "tester@example.test"
OTHER = "someone.real@example.test"


@pytest.fixture
def post(monkeypatch):
    monkeypatch.setenv("CLOUD_FUNCTION_URL", "https://email.example.test")
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "service-key")
    monkeypatch.delenv("EMAIL_RECIPIENT_ALLOWLIST", raising=False)
    mock = Mock(return_value=Mock(status_code=200))
    monkeypatch.setattr("SLL.email_service.requests.post", mock)
    return mock


def payload(to):
    return {"subject": "s", "content": "c", "to": to, "is_html": True}


def test_without_the_variable_the_payload_goes_unchanged_to_the_cloud_function(post):
    body = payload(f"{ALLOWED}, {OTHER}")

    response = email_service.send_email(body)

    assert response.status_code == 200
    post.assert_called_once_with(
        "https://email.example.test/send-email", json=body,
        headers={"X-API-Key": "service-key", "Content-Type": "application/json"},
    )


def test_the_status_of_the_cloud_function_is_returned_not_hidden(post):
    post.return_value = Mock(status_code=502)

    assert email_service.send_email(payload([ALLOWED])).status_code == 502


@pytest.mark.parametrize("value", ["", " , "])
def test_an_empty_variable_changes_nothing(post, monkeypatch, value):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", value)

    email_service.send_email(payload([ALLOWED, OTHER]))

    assert post.call_args.kwargs["json"]["to"] == [ALLOWED, OTHER]


def test_recipients_outside_the_list_are_dropped_keeping_the_shape_of_the_field(post, monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", f"  {ALLOWED.upper()} , other@example.test")

    email_service.send_email(payload([ALLOWED, OTHER]))
    assert post.call_args.kwargs["json"]["to"] == [ALLOWED]

    email_service.send_email(payload(f"{ALLOWED}, {OTHER}"))
    assert post.call_args.kwargs["json"]["to"] == ALLOWED


def test_nobody_allowed_means_no_delivery_and_a_clear_202(post, monkeypatch, caplog):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", ALLOWED)

    response = email_service.send_email(payload([OTHER]))

    assert response.status_code == 202
    assert "EMAIL_RECIPIENT_ALLOWLIST" in response.json()["message"]
    post.assert_not_called()


def test_removals_are_logged_without_the_address(post, monkeypatch, caplog):
    import logging

    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", ALLOWED)
    with caplog.at_level(logging.INFO):
        email_service.send_email(payload([ALLOWED, OTHER]))

    text = " ".join(record.getMessage() for record in caplog.records)
    assert "removed 1 recipient" in text
    assert OTHER not in text and OTHER.split("@")[0] not in text


def test_the_senders_use_the_cloud_function_and_keep_the_recipients_of_the_base(client, post, monkeypatch):
    from BLL import send_emails
    from Tests.helpers import create_draft

    monkeypatch.delenv("FLASK_ENV", raising=False)
    event_id = create_draft(client)

    response = send_emails.send_reservation_info_to_reitoria(event_id)

    assert response.status_code == 200
    (url,), kwargs = post.call_args
    assert url == "https://email.example.test/send-email"
    assert kwargs["headers"]["X-API-Key"] == "service-key"
    assert kwargs["json"]["to"] == ", ".join(send_emails.emails["reitoria"])
    assert kwargs["json"]["is_html"] is True
