"""Logs sem token, sem corpo de requisição e sem texto de exceção; saída em stdout."""

import logging
import sys

import pytest

from SLL.py_log import AppLogger, LogType, Logmessage, _handlers, mask_token, scrub_secrets
from Tests.helpers import EVENT, OWNER, create_draft, headers, slot

TOKEN = "SENTINELA-TOKEN-9f3a"
BODY = "SENTINELA-CORPO-77c1"
ERROR = "SENTINELA-ERRO-5b2d"


def test_the_token_is_logged_only_as_a_fingerprint(caplog):
    with caplog.at_level(logging.INFO):
        AppLogger.log(Logmessage.TOKEN_FAILURE, LogType.INFO, token=TOKEN, email="a@udf.edu.br", ip_address="1.2.3.4")

    assert TOKEN not in caplog.text
    assert mask_token(TOKEN) in caplog.text


def test_free_text_with_a_labelled_secret_is_scrubbed(caplog):
    assert TOKEN not in scrub_secrets(f"calling https://x/y?token={TOKEN}&a=1")
    assert TOKEN not in scrub_secrets(f"headers: {{'x-api-key': '{TOKEN}'}}")
    with caplog.at_level(logging.INFO):
        AppLogger.log(f"upstream said token={TOKEN}", LogType.INFO)  # texto simples, sem enum
    assert TOKEN not in caplog.text and "upstream said" in caplog.text


def test_a_plain_text_message_no_longer_crashes_the_logger(caplog):
    with caplog.at_level(logging.WARNING):
        AppLogger.log("Parâmetro eventId não informado.", LogType.WARNING, ip_address="1.2.3.4")
    assert "Parâmetro eventId não informado." in caplog.text


def test_the_approval_start_failure_log_has_no_exception_text(client, monkeypatch, caplog):
    event_id = create_draft(client)

    def fail(**kwargs):
        raise ValueError(ERROR)

    monkeypatch.setattr("SLL.events_routes.send_to_coordenacao", fail)
    with caplog.at_level(logging.INFO):
        response = client.post(f"/events/{event_id}/submit", json={**EVENT, **slot()}, headers=headers(OWNER))

    assert response.status_code == 503
    assert "approval start failed" in caplog.text and "ValueError" in caplog.text
    assert ERROR not in caplog.text


def test_the_rooms_search_failure_logs_the_body_size_not_the_body(client, monkeypatch, caplog):
    def boom(self, *args, **kwargs):
        raise RuntimeError(ERROR)

    monkeypatch.setattr("BLL.index.FlowController.filter_available_rooms", boom)
    with caplog.at_level(logging.INFO):
        response = client.get("/rooms/available-rooms?date=2031-03-01&time=10:00:00",
                              headers=headers(OWNER), data=BODY)

    assert response.status_code == 500
    assert BODY not in caplog.text and ERROR not in caplog.text
    assert "body_length=" in caplog.text


def test_the_log_goes_to_stdout():
    assert any(isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
               for h in _handlers())
