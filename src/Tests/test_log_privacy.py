"""Logs carry no request body, URL or exception text."""

import logging

import pytest
import requests
from mongomock import MongoClient

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


# --- remaining log and stdout call sites ------------------------------------------


def test_pdf_fetch_error_log_has_no_exception_text(client, monkeypatch, caplog):
    from SLL import events_routes, signed_links

    class BrokenManager:
        def get_pdf_by_event_id(self, event_id):
            raise RuntimeError(ERROR_SENTINEL)

    monkeypatch.setattr(events_routes, "ReservationManager", BrokenManager)
    with caplog.at_level(logging.INFO):
        response = client.get(f"/events/event-123/pdf?{signed_links.signed_query("event-123")}")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal Server Error"}
    assert "PDF fetch failed" in caplog.text
    assert "RuntimeError" in caplog.text
    assert "event-123" in caplog.text
    assert ERROR_SENTINEL not in caplog.text


def test_events_listing_error_log_has_no_exception_text(client, monkeypatch, caplog):
    from BLL import FlowController

    def crash(*args, **kwargs):
        raise RuntimeError(ERROR_SENTINEL)

    monkeypatch.setattr(FlowController, "find_events_by_user_email", crash)
    with caplog.at_level(logging.INFO):
        response = client.get("/events", headers=headers(OWNER))

    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal Server Error"}
    assert "Events listing failed" in caplog.text
    assert "RuntimeError" in caplog.text
    assert ERROR_SENTINEL not in caplog.text


def test_plain_text_log_message_is_written_as_is(caplog):
    from SLL.py_log import AppLogger, LogType

    with caplog.at_level(logging.INFO):
        AppLogger.log("mensagem pronta {sem_campo}", LogType.WARNING)

    assert "mensagem pronta {sem_campo}" in caplog.text


def test_room_lookup_does_not_print_the_rejected_input(client, capsys):
    from DAL import ReservationManager

    assert ReservationManager().find_unavailable_room_ids_by_date(ERROR_SENTINEL, "10:00:00") == []

    captured = capsys.readouterr()
    assert "ValueError" in captured.out
    assert ERROR_SENTINEL not in captured.out + captured.err


def test_minio_failure_does_not_print_exception_text(client, monkeypatch, capsys, tmp_path):
    from BLL import pdf

    class BrokenMinio:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(ERROR_SENTINEL)

    class FakeReservationManager:
        def insert_pdf(self, document):
            pass

    monkeypatch.setenv("MINIO_URL", "http://minio.test:9000")
    monkeypatch.setattr(pdf, "Minio", BrokenMinio)
    monkeypatch.setattr(pdf, "ReservationManager", FakeReservationManager)
    pdf_path = tmp_path / "event.pdf"
    pdf_path.write_bytes(b"%PDF-test")

    pdf.save_pdf("event-123", str(pdf_path))

    captured = capsys.readouterr()
    assert "RuntimeError" in captured.out
    assert ERROR_SENTINEL not in captured.out + captured.err


def test_pdf_date_failure_does_not_print_exception_text(monkeypatch, capsys):
    from datetime import datetime
    from BLL import pdf

    class BadDate(datetime):
        def strftime(self, fmt):
            raise ValueError(ERROR_SENTINEL)

    monkeypatch.setattr(pdf.FlowController, "find_types_by_collection", lambda name: [])
    monkeypatch.setattr(pdf, "get_name_by_idODS", lambda ods, ods_id: "ODS")
    monkeypatch.setattr(pdf.FlowController, "find_event_by_event_id", lambda event_id: {"odsId": "1"})
    monkeypatch.setattr(
        pdf.FlowController,
        "find_reservation_by_event_id",
        lambda event_id: {"startAt": BadDate(2031, 3, 1, 10), "endAt": BadDate(2031, 3, 1, 12)},
    )
    with pytest.raises(KeyError):  # the rest of the event data is absent; the print happens before
        pdf.generate_event_pdf(event_id="event-123")

    captured = capsys.readouterr()
    assert "ValueError" in captured.out
    assert ERROR_SENTINEL not in captured.out + captured.err


def test_index_creation_failure_log_has_no_exception_text(monkeypatch, caplog):
    import configmodule
    from SLL import create_app

    def crash():
        raise RuntimeError(ERROR_SENTINEL)

    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr(configmodule.Config, "MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setattr(configmodule.Config, "MONGO_DATABASE", "labtech_test")
    monkeypatch.setattr("DAL.ReservationManager.ensure_indexes", staticmethod(crash))
    with caplog.at_level(logging.INFO):
        create_app(configmodule.get_config())

    assert "active-reservation unique index" in caplog.text
    assert "RuntimeError" in caplog.text
    assert ERROR_SENTINEL not in caplog.text
    assert "Traceback" not in caplog.text
