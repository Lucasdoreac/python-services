import importlib

import pytest
from flask import url_for


@pytest.fixture
def make_app(monkeypatch):
    """Cria o app com as variáveis dadas. configmodule lê o ambiente na
    importação, por isso é recarregado (e recarregado de novo no fim)."""
    import configmodule
    # Mongo em memória: conftest.py (mongo_in_memory).

    def build(**env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        from SLL import create_app
        return create_app(importlib.reload(configmodule).get_config())

    yield build
    monkeypatch.undo()
    importlib.reload(configmodule)


@pytest.mark.parametrize("flask_env", ["production", "development"])
def test_approval_links_use_server_scheme(make_app, flask_env):
    # SERVER_SCHEME era lida mas não fazia nada: a ProductionConfig fixava
    # PREFERRED_URL_SCHEME="http", e atrás de HTTPS os links de aprovar/
    # rejeitar dos e-mails saíam com http://.
    app = make_app(FLASK_ENV=flask_env, SERVER_NAME="reservas.exemplo", SERVER_SCHEME="https")

    # Mesmo jeito que send_emails.py monta os links.
    with app.app_context(), app.test_request_context():
        link = url_for("templates_bp.approve", eventId="ev1", tokenId="t1", who="reitoria", _external=True)

    assert link.startswith("https://reservas.exemplo/")


def test_scheme_defaults_to_http(make_app):
    app = make_app(FLASK_ENV="production", SERVER_NAME="localhost:5000")

    with app.app_context(), app.test_request_context():
        link = url_for("templates_bp.approve", eventId="ev1", tokenId="t1", who="reitoria", _external=True)

    assert link.startswith("http://localhost:5000/")
