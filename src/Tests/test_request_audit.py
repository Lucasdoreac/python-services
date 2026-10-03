"""One audit line per authenticated request; never a token, an e-mail or a body."""

import logging

import pytest
from flask import Flask, abort, jsonify

from SLL import auth_decorators
from SLL.auth_upstream import DENIED, OK
from SLL.py_log import mask_email

EMAIL = "pessoa.teste@udf.edu.br"
TOKEN = "tok-visible-only-to-the-caller-0123456789"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth_decorators, "call_auth", lambda *a, **k: (OK, None))
    app = Flask(__name__)

    @app.route("/ping", methods=["GET", "POST"])
    @auth_decorators.token_required
    def ping():
        return jsonify(ok=True), 201

    @app.route("/missing")
    @auth_decorators.token_required
    def missing():
        return jsonify(error="no"), 404

    @app.route("/gone")
    @auth_decorators.token_required
    def gone():
        abort(404)

    @app.route("/boom")
    @auth_decorators.token_required
    def boom():
        raise RuntimeError("view failed")

    return app.test_client()


def audit_lines(caplog):
    return [r.getMessage() for r in caplog.records if "Authenticated request" in r.getMessage()]


def test_success_writes_one_line_with_hash_method_path_and_status(client, caplog):
    with caplog.at_level(logging.INFO):
        client.get("/ping", headers={"token": TOKEN, "email": EMAIL})
    (line,) = audit_lines(caplog)
    assert f"email_hash: {mask_email(EMAIL)}" in line
    assert "method: GET" in line and "path: /ping" in line and "status: 201" in line


def test_the_line_never_carries_the_token_the_email_the_query_or_the_body(client, caplog):
    with caplog.at_level(logging.DEBUG):
        client.post(f"/ping?token={TOKEN}&email={EMAIL}", json={"secret": "body-value"})
        client.get("/ping", headers={"token": TOKEN, "email": EMAIL})
    text = caplog.text
    assert audit_lines(caplog)
    for forbidden in (TOKEN, EMAIL, "body-value", "token=", "email="):
        assert forbidden not in text


def test_the_status_of_error_answers_is_recorded(client, caplog):
    with caplog.at_level(logging.INFO):
        client.get("/missing", headers={"token": TOKEN, "email": EMAIL})
    assert "status: 404" in audit_lines(caplog)[0]


def test_a_view_that_raises_is_logged_as_500_and_still_raises(client, caplog):
    client.application.config["PROPAGATE_EXCEPTIONS"] = True
    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError):
        client.get("/boom", headers={"token": TOKEN, "email": EMAIL})
    assert "status: 500" in audit_lines(caplog)[0]


def test_a_denied_token_does_not_write_the_success_line(client, caplog, monkeypatch):
    monkeypatch.setattr(auth_decorators, "call_auth", lambda *a, **k: (DENIED, None))
    with caplog.at_level(logging.INFO):
        response = client.get("/ping", headers={"token": TOKEN, "email": EMAIL})
    assert response.status_code == 403
    assert audit_lines(caplog) == []


def test_the_fingerprint_is_keyed_not_a_plain_hash(monkeypatch):
    import hashlib

    monkeypatch.setenv("INTERNAL_API_KEY", "key-one")
    first = mask_email(EMAIL)
    plain = hashlib.sha256(EMAIL.encode()).hexdigest()
    assert plain[:12] not in first                       # not the guessable unsalted hash
    assert mask_email(EMAIL.upper()) == first            # case-insensitive, stable
    assert mask_email("outra.pessoa@udf.edu.br") != first
    monkeypatch.setenv("INTERNAL_API_KEY", "key-two")
    assert mask_email(EMAIL) != first                    # depends on the key


def test_without_a_key_the_fingerprint_is_still_not_the_plain_hash(monkeypatch):
    import hashlib

    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    assert hashlib.sha256(EMAIL.encode()).hexdigest()[:12] not in mask_email(EMAIL)


def test_an_abort_is_logged_with_the_status_flask_answers(client, caplog):
    with caplog.at_level(logging.INFO):
        response = client.get("/gone", headers={"token": TOKEN, "email": EMAIL})
    assert response.status_code == 404
    assert "status: 404" in audit_lines(caplog)[0]


def test_the_line_carries_the_client_address_behind_the_proxy_not_the_proxy(client, caplog, monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    with caplog.at_level(logging.INFO):
        client.get("/ping", headers={"token": TOKEN, "email": EMAIL, "X-Forwarded-For": "203.0.113.50"})
    assert "203.0.113.50" in audit_lines(caplog)[0]
