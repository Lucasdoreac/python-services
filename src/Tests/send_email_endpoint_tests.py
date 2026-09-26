"""Testes do endpoint POST /send-email (contrato com auth_service e Brevo).

Antes: o código chamava {CLOUD_FUNCTION_URL}/send-email, mas essa função não
existia em lugar nenhum da organização. Agora o python-services expõe a rota
protegida por X-API-Key e despacha via Brevo (ou dry run em desenvolvimento).
"""
import pytest
from unittest.mock import MagicMock
from mongomock import MongoClient

from configmodule import get_config
from SLL import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    app = create_app(get_config())
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_send_email_requires_api_key(client, monkeypatch):
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "chave-secreta")
    from settings import get_email_settings
    get_email_settings.cache_clear()

    # Sem header
    res = client.post("/send-email", json={"to": ["teste@udf.edu.br"], "subject": "Oi", "content": "Olá"})
    assert res.status_code == 401

    # Com chave errada
    res = client.post(
        "/send-email",
        headers={"X-API-Key": "chave-errada"},
        json={"to": ["teste@udf.edu.br"], "subject": "Oi", "content": "Olá"},
    )
    assert res.status_code == 401


def test_send_email_validates_payload(client, monkeypatch):
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "chave-secreta")
    from settings import get_email_settings
    get_email_settings.cache_clear()

    headers = {"X-API-Key": "chave-secreta"}

    # Faltando 'to'
    res = client.post("/send-email", headers=headers, json={"subject": "Oi", "content": "Olá"})
    assert res.status_code == 400
    assert "to" in res.get_json().get("error", "").lower()

    # Faltando 'subject'
    res = client.post("/send-email", headers=headers, json={"to": ["a@udf.edu.br"], "content": "Olá"})
    assert res.status_code == 400
    assert "subject" in res.get_json().get("error", "").lower()

    # Faltando 'content'
    res = client.post("/send-email", headers=headers, json={"to": ["a@udf.edu.br"], "subject": "Oi"})
    assert res.status_code == 400
    assert "content" in res.get_json().get("error", "").lower()


def test_send_email_dry_run_returns_200(client, monkeypatch):
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "chave-secreta")
    monkeypatch.setenv("EMAIL_DRY_RUN", "true")
    from settings import get_email_settings
    get_email_settings.cache_clear()

    headers = {"X-API-Key": "chave-secreta"}
    payload = {
        "to": ["professor@udf.edu.br"],
        "subject": "Autorização de Acesso",
        "content": "<p>Clique aqui</p>",
        "is_html": True,
    }
    res = client.post("/send-email", headers=headers, json=payload)
    assert res.status_code == 200
    body = res.get_json()
    assert body.get("status") == "sent"
    assert body.get("dry_run") is True


def test_send_email_with_brevo_dispatches_message(client, monkeypatch):
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "chave-secreta")
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_RECIPIENTS_COORDENACAO", "coord@udf.edu.br")
    monkeypatch.setenv("EMAIL_RECIPIENTS_REITORIA", "reitoria@udf.edu.br")
    monkeypatch.setenv("CLOUD_FUNCTION_URL", "http://127.0.0.1:5000")
    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-fake-api-key")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "remetente@udf.edu.br")
    monkeypatch.setenv("BREVO_SENDER_NAME", "Reservas UDF")
    from settings import get_email_settings
    get_email_settings.cache_clear()

    mock_send = MagicMock(return_value=MagicMock(message_id="msg-123"))
    monkeypatch.setattr("SLL.brevo_service.send_brevo_email", mock_send)

    headers = {"X-API-Key": "chave-secreta"}
    payload = {
        "to": "professor@udf.edu.br",
        "subject": "Seu link",
        "content": "http://link",
        "is_html": False,
    }
    res = client.post("/send-email", headers=headers, json=payload)
    assert res.status_code == 200
    assert res.get_json().get("status") == "sent"

    mock_send.assert_called_once()
    _, kwargs = mock_send.call_args
    assert kwargs["to"] == ["professor@udf.edu.br"]
    assert kwargs["subject"] == "Seu link"
    assert kwargs["content"] == "http://link"
    assert kwargs["is_html"] is False
