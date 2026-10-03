"""AppLogger records the client address, not the platform proxy's."""

import logging

import pytest
from flask import Flask, jsonify

from SLL import auth_decorators
from SLL.auth_upstream import DENIED
from SLL.py_log import AppLogger, LogType, Logmessage

PROXY = "127.0.0.1"
CLIENT = "203.0.113.7"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    app = Flask(__name__)

    @app.route("/log")
    def log_route():
        AppLogger.log(Logmessage.EVENTS_NOT_FOUND, LogType.INFO)
        return jsonify(ok=True)

    @app.route("/explicit")
    def explicit_route():
        AppLogger.log(Logmessage.EVENTS_NOT_FOUND, LogType.INFO, ip_address="10.9.9.9")
        return jsonify(ok=True)

    @app.route("/guarded")
    @auth_decorators.token_required
    def guarded():
        return jsonify(ok=True)

    return app


def _lines(caplog):
    return [r.getMessage() for r in caplog.records]


def test_forwarded_client_is_logged_with_default_hop(app, caplog):
    with caplog.at_level(logging.INFO):
        app.test_client().get(
            "/log",
            headers={"X-Forwarded-For": CLIENT},
            environ_overrides={"REMOTE_ADDR": PROXY},
        )
    (line,) = _lines(caplog)
    assert f"IP: {CLIENT}" in line
    assert PROXY not in line


def test_spoofed_leftmost_entry_is_ignored(app, caplog):
    with caplog.at_level(logging.INFO):
        app.test_client().get(
            "/log",
            headers={"X-Forwarded-For": f"6.6.6.6, {CLIENT}"},
            environ_overrides={"REMOTE_ADDR": PROXY},
        )
    (line,) = _lines(caplog)
    assert f"IP: {CLIENT}" in line
    assert "6.6.6.6" not in line


def test_without_forwarded_header_falls_back_to_remote_addr(app, caplog):
    with caplog.at_level(logging.INFO):
        app.test_client().get("/log", environ_overrides={"REMOTE_ADDR": "198.51.100.4"})
    (line,) = _lines(caplog)
    assert "IP: 198.51.100.4" in line


def test_explicit_ip_address_is_kept(app, caplog):
    with caplog.at_level(logging.INFO):
        app.test_client().get("/explicit", headers={"X-Forwarded-For": CLIENT})
    (line,) = _lines(caplog)
    assert "IP: 10.9.9.9" in line


def test_outside_a_request_nothing_breaks(caplog):
    with caplog.at_level(logging.INFO):
        AppLogger.log(Logmessage.EVENTS_NOT_FOUND, LogType.INFO)
        AppLogger.log(Logmessage.EVENTS_NOT_FOUND, LogType.INFO, ip_address="job")
    assert any("IP: job" in line for line in _lines(caplog))


def test_auth_failure_line_carries_forwarded_client(app, monkeypatch, caplog):
    monkeypatch.setattr(auth_decorators, "call_auth", lambda *a, **k: (DENIED, None))
    with caplog.at_level(logging.INFO):
        response = app.test_client().get(
            "/guarded",
            headers={"email": "a@udf.edu.br", "token": "tok-123456789", "X-Forwarded-For": CLIENT},
            environ_overrides={"REMOTE_ADDR": PROXY},
        )
    assert response.status_code == 403
    (line,) = _lines(caplog)
    assert f"IP: {CLIENT}" in line
