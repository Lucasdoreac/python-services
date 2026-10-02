"""Logs carry no request body, URL or exception text."""

import logging

import requests

from Tests.test_event_submission import (  # noqa: F401
    EVENT, OWNER, client, create_draft, headers, slot,
)

BODY_SENTINEL = "SENTINELA-CORPO-9f3a"
ERROR_SENTINEL = "SENTINELA-ERRO-7c21"


def test_rooms_error_log_has_no_body_or_exception_text(client, monkeypatch, caplog):
    from BLL import FlowController

    def crash(*args, **kwargs):
        raise RuntimeError(ERROR_SENTINEL)

    monkeypatch.setattr(FlowController, "filter_available_rooms", crash)
    with caplog.at_level(logging.INFO):
        response = client.get(
            "/rooms/available-rooms?date=2031-03-01&time=10:00:00",
            data=BODY_SENTINEL,
            headers=headers(OWNER),
        )

    assert response.status_code == 500
    assert "Internal APIs crashed" in caplog.text
    assert BODY_SENTINEL not in caplog.text
    assert ERROR_SENTINEL not in caplog.text
    assert "RuntimeError" in caplog.text
    assert f"body_length={len(BODY_SENTINEL)}" in caplog.text


def test_approval_start_failure_log_has_no_exception_text(client, monkeypatch, caplog):
    def crash(**kwargs):
        raise RuntimeError(ERROR_SENTINEL)

    monkeypatch.setattr("SLL.events_routes.pdf.generate_event_pdf", crash)
    event_id = create_draft(client)
    with caplog.at_level(logging.INFO):
        response = client.post(
            f"/events/{event_id}/submit", json={**EVENT, **slot()}, headers=headers(OWNER)
        )

    assert response.status_code == 200
    assert "approval start failed" in caplog.text
    assert ERROR_SENTINEL not in caplog.text


def test_auth_unavailable_log_has_no_exception_text(monkeypatch, caplog):
    from flask import Flask
    from BLL import authentication

    def crash(*args, **kwargs):
        raise requests.exceptions.ConnectionError(f"https://auth.test/{ERROR_SENTINEL}")

    monkeypatch.setattr(authentication, "call_auth", crash)
    with caplog.at_level(logging.INFO), Flask(__name__).test_request_context():
        response = authentication.AuthenticationController.insert_token("user@udf.edu.br")

    assert response.status_code == 503
    assert ERROR_SENTINEL not in caplog.text
