import pytest

from SLL.insecure_dev import insecure_dev_allowed
from SLL.startup_checks import require_internal_api_key


def test_starts_with_the_key(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "a-key")
    require_internal_api_key()


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_empty_or_blank_key_stops_the_start(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    else:
        monkeypatch.setenv("INTERNAL_API_KEY", value)
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("ALLOW_INSECURE_DEV", raising=False)
    with pytest.raises(RuntimeError, match="INTERNAL_API_KEY"):
        require_internal_api_key()


def test_the_opt_out_needs_both_variables(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("ALLOW_INSECURE_DEV", "true")
    require_internal_api_key()
    assert insecure_dev_allowed()

    monkeypatch.setenv("FLASK_ENV", "production")
    assert not insecure_dev_allowed()
    with pytest.raises(RuntimeError):
        require_internal_api_key()

    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("ALLOW_INSECURE_DEV", "false")
    with pytest.raises(RuntimeError):
        require_internal_api_key()


# --- login-link limit per client -------------------------------------------------

from flask import Flask

from SLL import client_limits


def link_client(monkeypatch):
    import SLL.auth_routes as routes

    client_limits.reset()
    monkeypatch.setenv("AUTH_EMAIL_ALLOWLIST", "")
    sent = []

    class FakeController:
        @staticmethod
        def insert_token(email):
            sent.append(email)
            return {"message": "ok"}, 201

    monkeypatch.setattr(routes, "AuthenticationController", FakeController)
    app = Flask(__name__)
    app.register_blueprint(routes.auth_bp)
    return app.test_client(), sent


def test_each_client_gets_its_own_budget(monkeypatch):
    client, sent = link_client(monkeypatch)
    for i in range(10):
        r = client.post(f"/auth/send-link?email=u{i}@udf.edu.br", headers={"X-Forwarded-For": "203.0.113.5"})
        assert r.status_code == 201
    limited = client.post("/auth/send-link?email=x@udf.edu.br", headers={"X-Forwarded-For": "203.0.113.5"})
    assert limited.status_code == 429 and limited.headers["Retry-After"] == "900"
    assert client.post("/auth/send-link?email=y@udf.edu.br",
                       headers={"X-Forwarded-For": "203.0.113.6"}).status_code == 201


def test_spoofed_leftmost_forwarded_entries_do_not_reset_the_budget(monkeypatch):
    client, sent = link_client(monkeypatch)
    codes = [client.post(f"/auth/send-link?email=u{i}@udf.edu.br",
                         headers={"X-Forwarded-For": f"10.9.9.{i}, 198.51.100.7"}).status_code
             for i in range(12)]
    assert codes[:10] == [201] * 10 and codes[10:] == [429, 429]


def test_invalid_domains_do_not_consume_the_budget(monkeypatch):
    client, sent = link_client(monkeypatch)
    for _ in range(15):
        assert client.post("/auth/send-link?email=a@example.invalid",
                           headers={"X-Forwarded-For": "203.0.113.5"}).status_code == 400
    assert client.post("/auth/send-link?email=ok@udf.edu.br",
                       headers={"X-Forwarded-For": "203.0.113.5"}).status_code == 201
