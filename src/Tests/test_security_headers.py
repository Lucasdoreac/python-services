import pytest
from flask import Flask, jsonify

from SLL.security_headers import apply_security_headers, docs_enabled


@pytest.fixture
def client():
    app = Flask(__name__)
    app.after_request(apply_security_headers)

    @app.route("/json")
    def as_json():
        return jsonify(ok=True)

    @app.route("/page")
    def page():
        return "<p>hi</p>"

    return app.test_client()


def test_every_answer_carries_the_basic_headers(client):
    for path in ("/json", "/page", "/missing"):
        headers = client.get(path).headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "no-referrer"


def test_json_gets_a_strict_csp_but_html_pages_do_not(client):
    assert "default-src 'none'" in client.get("/json").headers["Content-Security-Policy"]
    assert "Content-Security-Policy" not in client.get("/page").headers


def test_hsts_only_over_https(client):
    assert "Strict-Transport-Security" not in client.get("/json").headers
    secure = client.get("/json", headers={"X-Forwarded-Proto": "https"})
    assert secure.headers["Strict-Transport-Security"].startswith("max-age=")


def test_docs_are_open_by_default_as_in_main(monkeypatch):
    monkeypatch.delenv("ENABLE_API_DOCS", raising=False)
    assert docs_enabled()
    monkeypatch.setenv("ENABLE_API_DOCS", "")  # vazio equivale a não definido
    assert docs_enabled()
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    assert docs_enabled()


def test_docs_close_only_with_an_explicit_false_value(monkeypatch):
    for value in ("false", "FALSE", "0", "no", "off"):
        monkeypatch.setenv("ENABLE_API_DOCS", value)
        assert not docs_enabled(), value


def test_app_serves_docs_by_default_and_closes_them_with_false(monkeypatch):
    from mongomock import MongoClient

    from configmodule import get_config
    from DAL import MongoDBConnectionFactory
    from SLL import create_app

    def build():
        # Mongo em memória e sem rede, como no conftest: o init_app não cria cliente real.
        monkeypatch.setattr(MongoDBConnectionFactory, "_client", MongoClient())
        monkeypatch.setattr(MongoDBConnectionFactory, "_database", "labtech_test")
        return create_app(get_config()).test_client()

    monkeypatch.delenv("ENABLE_API_DOCS", raising=False)
    monkeypatch.delenv("ALLOW_INSECURE_DEV", raising=False)
    client = build()
    assert client.get("/apispec_1.json").status_code == 200
    assert client.get("/apidocs/").status_code in (200, 301, 302)

    monkeypatch.setenv("ENABLE_API_DOCS", "false")
    client = build()
    assert client.get("/apispec_1.json").status_code == 404
    assert client.get("/apidocs/").status_code == 404
    assert client.get("/health").headers["X-Content-Type-Options"] == "nosniff"


# --- CORS ---------------------------------------------------------------------------

def cors_client(monkeypatch, **env):
    from flask_cors import CORS

    from SLL.security_headers import cors_origins

    for name in ("FRONTEND_URL", "CORS_ALLOWED_ORIGINS", "FLASK_ENV", "ALLOW_INSECURE_DEV"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    app = Flask(__name__)
    CORS(app, origins=cors_origins(), supports_credentials=False)

    @app.route("/x")
    def x():
        return "ok"

    return app.test_client()


def allowed(client, origin):
    return client.get("/x", headers={"Origin": origin}).headers.get("Access-Control-Allow-Origin")


def test_only_the_frontend_origin_is_allowed(monkeypatch):
    client = cors_client(monkeypatch, FRONTEND_URL="https://reservas-web.example.com/some/path")
    assert allowed(client, "https://reservas-web.example.com") == "https://reservas-web.example.com"
    assert allowed(client, "https://evil.example") is None
    assert allowed(client, "http://reservas-web.example.com") is None
    preflight = client.options("/x", headers={"Origin": "https://evil.example",
                                              "Access-Control-Request-Method": "GET"})
    assert "Access-Control-Allow-Origin" not in preflight.headers


def test_extra_origins_are_exact(monkeypatch):
    client = cors_client(monkeypatch, FRONTEND_URL="https://a.example.com",
                         CORS_ALLOWED_ORIGINS="https://b.example.com, https://c.example.com/")
    for origin in ("https://a.example.com", "https://b.example.com", "https://c.example.com"):
        assert allowed(client, origin) == origin
    assert allowed(client, "https://d.example.com") is None


def test_without_configuration_any_origin_is_allowed_as_in_main(monkeypatch):
    client = cors_client(monkeypatch)
    # flask_cors devolve a própria origem sob "*", igual ao CORS(app) da main.
    assert allowed(client, "https://reservas-web.example.com") == "https://reservas-web.example.com"
    assert allowed(client, "https://qualquer.example") == "https://qualquer.example"


def test_empty_configuration_values_count_as_not_defined(monkeypatch):
    from SLL.security_headers import cors_open_by_default

    monkeypatch.setenv("FRONTEND_URL", "  ")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    assert cors_open_by_default()


def test_open_cors_by_default_is_reported_and_configured_cors_is_not(monkeypatch):
    from SLL.security_headers import cors_open_by_default

    monkeypatch.delenv('FRONTEND_URL', raising=False)
    monkeypatch.delenv('CORS_ALLOWED_ORIGINS', raising=False)
    assert cors_open_by_default()
    monkeypatch.setenv("FRONTEND_URL", "https://a.example.com")
    assert not cors_open_by_default()
    monkeypatch.delenv("FRONTEND_URL")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://b.example.com")
    assert not cors_open_by_default()


def test_the_development_opt_out_is_the_only_wildcard(monkeypatch):
    client = cors_client(monkeypatch, FLASK_ENV="development", ALLOW_INSECURE_DEV="true")
    assert allowed(client, "http://anything.test") == "http://anything.test"  # any origin, development only
    client = cors_client(monkeypatch, FLASK_ENV="production", ALLOW_INSECURE_DEV="true",
                         FRONTEND_URL="https://a.example.com")
    assert allowed(client, "http://anything.test") is None  # opt-out ignored outside development
