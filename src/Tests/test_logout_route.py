"""POST /auth/logout forwards the caller's session to the Auth service for deletion."""

import logging

import pytest
from flask import Flask

from SLL import client_limits


def make_client(monkeypatch, outcome="ok", status=204, text=""):
    import BLL.authentication as bll
    import SLL.auth_routes as routes

    client_limits.reset()
    seen = []

    class Upstream:
        headers = {"Content-Type": "application/json"}

    Upstream.status_code, Upstream.text = status, text

    def fake_call(method, url, **kwargs):
        seen.append((method, url, kwargs))
        return outcome, Upstream()

    monkeypatch.setattr(bll, "call_auth", fake_call)
    monkeypatch.setenv("URL_AUTH", "https://auth.test")
    app = Flask(__name__)
    app.register_blueprint(routes.auth_bp)
    return app.test_client(), seen


SESSION = "S" * 43
BODY = {"email": "u@udf.edu.br", "token": SESSION}


def test_logout_forwards_the_pair_in_the_body_and_answers_204(monkeypatch):
    client, seen = make_client(monkeypatch)
    response = client.post("/auth/logout", json=BODY)
    assert response.status_code == 204 and response.data == b""
    method, url, kwargs = seen[0]
    assert (method, url) == ("POST", "https://auth.test/auth/logout")
    assert kwargs["json"] == BODY and not kwargs.get("params")      # never in the URL
    assert kwargs["retry_read_timeouts"] is False                    # the delete is not repeated blindly


def test_logout_never_echoes_or_logs_the_token(monkeypatch, caplog):
    client, _ = make_client(monkeypatch)
    with caplog.at_level(logging.DEBUG):
        response = client.post("/auth/logout", json=BODY)
    assert SESSION.encode() not in response.data and SESSION not in str(response.headers)
    assert SESSION not in caplog.text


def test_logout_validates_the_body_before_calling_the_auth(monkeypatch):
    client, seen = make_client(monkeypatch)
    for body in ({}, {"email": "u@udf.edu.br"}, {"token": "x"}, {"email": "u@udf.edu.br", "token": 5}):
        assert client.post("/auth/logout", json=body).status_code == 400
    assert client.post("/auth/logout", data="nope").status_code == 400
    assert seen == []


def test_logout_answers_503_with_wake_url_when_the_auth_sleeps(monkeypatch):
    import BLL.authentication as bll

    client, _ = make_client(monkeypatch)

    class Asleep:
        status_code = 502
        headers = {"x-render-routing": "no-deploy"}
        text = ""

    monkeypatch.setattr(bll, "call_auth", lambda *a, **k: ("unavailable", Asleep()))
    response = client.post("/auth/logout", json=BODY)
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "10"
    assert response.get_json()["wake_url"] == "https://auth.test/health"


def test_logout_relays_a_refusal_from_the_auth(monkeypatch):
    client, _ = make_client(monkeypatch, outcome="denied", status=429, text='{"error": "Too many requests; try again later"}')
    response = client.post("/auth/logout", json=BODY)
    assert response.status_code == 429 and response.get_json() == {"error": "Too many requests; try again later"}


def test_logout_is_limited_per_client(monkeypatch):
    from SLL.auth_routes import LOGOUT_PER_CLIENT

    client, seen = make_client(monkeypatch)
    codes = [client.post("/auth/logout", json=BODY).status_code for _ in range(LOGOUT_PER_CLIENT + 3)]
    assert codes[:LOGOUT_PER_CLIENT] == [204] * LOGOUT_PER_CLIENT and codes[LOGOUT_PER_CLIENT:] == [429] * 3
    assert len(seen) == LOGOUT_PER_CLIENT


def test_logout_forwards_the_client_to_the_auth_like_the_other_calls(monkeypatch):
    monkeypatch.setenv("AUTH_FORWARD_KEY", "k")
    client, seen = make_client(monkeypatch)
    client.post("/auth/logout", json=BODY, headers={"X-Forwarded-For": "203.0.113.9"})
    assert seen[0][2]["headers"] == {"X-Client-IP": "203.0.113.9", "X-Forward-Key": "k"}
