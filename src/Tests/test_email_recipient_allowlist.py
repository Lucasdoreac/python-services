"""Optional EMAIL_RECIPIENT_ALLOWLIST: test environments only deliver to the addresses it lists."""
import logging
from unittest.mock import Mock

import pytest
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory
from SLL import create_app

ALLOWED = "tester@example.test"
OTHER = "someone.real@example.test"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    monkeypatch.setattr(MongoDBConnectionFactory, "_client", MongoClient())
    monkeypatch.setattr(MongoDBConnectionFactory, "_database", "api_email_allowlist_test")
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "service-key")
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setenv("BREVO_API_KEY", "brevo-key")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "sender@example.test")
    monkeypatch.delenv("EMAIL_RECIPIENT_ALLOWLIST", raising=False)
    return create_app(get_config()).test_client()


@pytest.fixture
def provider(monkeypatch):
    response = Mock(content=b'{"messageId": "m-1"}', status_code=201)
    response.json.return_value = {"messageId": "m-1"}
    post = Mock(return_value=response)
    monkeypatch.setattr("SLL.email_routes.requests.post", post)
    return post


def send(client, recipients):
    return client.post(
        "/send-email", headers={"X-API-Key": "service-key"},
        json={"to": recipients, "subject": "Assunto", "content": "Texto"})


def delivered(provider):
    return [item["email"] for item in provider.call_args.kwargs["json"]["to"]]


def test_without_the_variable_every_recipient_is_delivered(client, provider):
    assert send(client, [ALLOWED, OTHER]).status_code == 200
    assert delivered(provider) == [ALLOWED, OTHER]


def test_an_empty_variable_changes_nothing(client, provider, monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", " , ")
    assert send(client, [ALLOWED, OTHER]).status_code == 200
    assert delivered(provider) == [ALLOWED, OTHER]


def test_recipients_outside_the_list_are_dropped(client, provider, monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", f"  {ALLOWED.upper()} , other@example.test")
    response = send(client, [ALLOWED, OTHER])
    assert response.status_code == 200
    assert delivered(provider) == [ALLOWED]


def test_nobody_allowed_means_no_delivery_and_a_clear_202(client, provider, monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", ALLOWED)
    response = send(client, [OTHER])
    assert response.status_code == 202
    assert "destinatário" in response.get_json()["message"]
    provider.assert_not_called()


def test_the_filter_also_applies_in_dry_run(client, provider, monkeypatch):
    monkeypatch.setenv("EMAIL_DRY_RUN", "true")
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", ALLOWED)
    assert send(client, [OTHER]).status_code == 202
    provider.assert_not_called()


def test_removals_are_logged_without_the_address(client, provider, monkeypatch, caplog):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", ALLOWED)
    with caplog.at_level(logging.INFO):
        send(client, [ALLOWED, OTHER])
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "hmac:" in text
    assert OTHER not in text and OTHER.split("@")[0] not in text
