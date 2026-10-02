"""Auth cold start: timeouts, retries and an explicit 503 instead of a 403."""

import pytest
import requests
from flask import Flask

from SLL import auth_upstream
from SLL.auth_decorators import token_required

URL = "http://auth.test/auth/validate"


class FakeResponse:
    def __init__(self, status_code, content_type=None, routing=None):
        self.status_code = status_code
        self.headers = {"content-type": content_type} if content_type else {}
        if routing:
            self.headers["x-render-routing"] = routing
        self.text = "<html>Service waking up</html>"

    def __bool__(self):
        return self.status_code < 400


class Clock:
    """Fake monotonic clock; sleeping advances it so budgets are deterministic."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def script(monkeypatch, results, clock, per_call=1.0):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(timeout)
        clock.now += per_call
        result = results[min(len(calls) - 1, len(results) - 1)]
        if isinstance(result, Exception):
            raise result
        if isinstance(result, tuple):
            return FakeResponse(*result)
        return FakeResponse(result)

    monkeypatch.setattr("SLL.auth_upstream.requests.get", fake_get)
    monkeypatch.setattr("SLL.auth_upstream.requests.post", fake_get)
    return calls


def call(clock, method="GET", **kwargs):
    return auth_upstream.call_auth(method, URL, sleep=clock.sleep, clock=clock, **kwargs)


def test_retries_until_auth_wakes(monkeypatch):
    monkeypatch.setenv("AUTH_UPSTREAM_BUDGET_SECONDS", "40")
    clock = Clock()
    calls = script(monkeypatch, [503, requests.exceptions.ConnectionError(), 503, 200], clock)
    outcome, response = call(clock)
    assert outcome == auth_upstream.OK and response.status_code == 200
    assert len(calls) == 4
    assert all(connect == auth_upstream.CONNECT_TIMEOUT and read <= 15 for connect, read in calls)


def test_denied_is_not_retried(monkeypatch):
    clock = Clock()
    calls = script(monkeypatch, [403, 200], clock)
    outcome, response = call(clock)
    assert outcome == auth_upstream.DENIED and response.status_code == 403
    assert len(calls) == 1


def test_platform_html_error_is_not_a_denial(monkeypatch):
    monkeypatch.setenv("AUTH_UPSTREAM_BUDGET_SECONDS", "40")
    clock = Clock()
    calls = script(monkeypatch, [(403, "text/html"), (404, "text/html"), (200, "application/json")], clock)
    outcome, response = call(clock)
    assert outcome == auth_upstream.OK and len(calls) == 3


def test_json_4xx_from_auth_is_a_denial(monkeypatch):
    clock = Clock()
    calls = script(monkeypatch, [(403, "application/json"), 200], clock)
    outcome, _ = call(clock)
    assert outcome == auth_upstream.DENIED and len(calls) == 1


def test_unavailable_after_budget(monkeypatch):
    monkeypatch.setenv("AUTH_UPSTREAM_BUDGET_SECONDS", "10")
    clock = Clock()
    calls = script(monkeypatch, [503], clock)
    outcome, response = call(clock)
    assert outcome == auth_upstream.UNAVAILABLE
    assert 2 <= len(calls) <= 5
    assert clock.now <= 10 + auth_upstream.RETRY_DELAY


def test_read_timeout_on_side_effect_call_is_not_retried(monkeypatch):
    clock = Clock()
    calls = script(monkeypatch, [requests.exceptions.ReadTimeout(), 200], clock)
    outcome, response = call(clock, "POST", retry_read_timeouts=False)
    assert outcome == auth_upstream.UNAVAILABLE and response is None
    assert len(calls) == 1


def make_client():
    app = Flask(__name__)

    @app.route("/protected")
    @token_required
    def protected():
        return "ok"

    return app.test_client()


HEADERS = {"email": "user@udf.edu.br", "token": "t"}


@pytest.fixture(autouse=True)
def fast_budget(monkeypatch):
    monkeypatch.setenv("URL_AUTH", "http://auth.test")
    monkeypatch.setenv("AUTH_UPSTREAM_BUDGET_SECONDS", "3")


def test_decorator_returns_503_when_auth_is_down(monkeypatch):
    clock = Clock()
    script(monkeypatch, [503], clock)
    monkeypatch.setattr("SLL.auth_upstream.time.sleep", clock.sleep)
    monkeypatch.setattr("SLL.auth_upstream.time.monotonic", clock)
    response = make_client().get("/protected", headers=HEADERS)
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "10"
    assert "unavailable" in response.get_json()["error"]


def test_decorator_keeps_403_for_invalid_token(monkeypatch):
    script(monkeypatch, [403], Clock())
    response = make_client().get("/protected", headers=HEADERS)
    assert response.status_code == 403
    assert response.get_json() == {"error": "Token validation failed"}


def test_decorator_passes_valid_token(monkeypatch):
    script(monkeypatch, [200], Clock())
    assert make_client().get("/protected", headers=HEADERS).data == b"ok"


def test_transient_log_never_prints_json_values(monkeypatch, capsys):
    class JsonResponse(FakeResponse):
        def json(self):
            return {"error": "bad", "email": "someone@udf.edu.br", "token": "SECRET"}

    monkeypatch.setenv("AUTH_UPSTREAM_BUDGET_SECONDS", "1")
    monkeypatch.setattr("SLL.auth_upstream.requests.get",
                        lambda *a, **k: JsonResponse(503, "application/json"))
    clock = Clock()
    auth_upstream.call_auth("GET", URL, sleep=clock.sleep, clock=clock)
    out = capsys.readouterr().out
    assert "json_keys=['email', 'error', 'token']" in out
    assert "someone@udf.edu.br" not in out and "SECRET" not in out


def test_transient_log_prints_body_only_for_platform_pages(monkeypatch, capsys):
    monkeypatch.setenv("AUTH_UPSTREAM_BUDGET_SECONDS", "1")
    monkeypatch.setattr("SLL.auth_upstream.requests.get",
                        lambda *a, **k: FakeResponse(503, "text/html"))
    clock = Clock()
    auth_upstream.call_auth("GET", URL, sleep=clock.sleep, clock=clock)
    assert "Service waking up" in capsys.readouterr().out


ASLEEP = (502, "text/html; charset=utf-8", "no-deploy")


def test_sleeping_auth_fails_fast_with_wake_url(monkeypatch):
    clock = Clock()
    calls = script(monkeypatch, [ASLEEP, 200], clock)
    outcome, response = call(clock)
    assert outcome == auth_upstream.UNAVAILABLE and len(calls) == 1
    payload = auth_upstream.unavailable_payload(response)
    assert payload["wake_url"] == "http://auth.test/health"
    assert "wake_url" not in auth_upstream.unavailable_payload(None)


def test_decorator_503_carries_wake_url_only_when_asleep(monkeypatch):
    script(monkeypatch, [ASLEEP], Clock())
    response = make_client().get("/protected", headers=HEADERS)
    assert response.status_code == 503
    assert response.get_json()["wake_url"] == "http://auth.test/health"
    assert response.headers["Retry-After"] == "10"


def test_send_link_returns_503_with_wake_url(monkeypatch):
    from BLL.authentication import AuthenticationController

    script(monkeypatch, [ASLEEP], Clock())
    app = Flask(__name__)
    with app.test_request_context():
        response = AuthenticationController.insert_token("user@udf.edu.br")
    assert response.status_code == 503
    assert b"http://auth.test/health" in response.data
