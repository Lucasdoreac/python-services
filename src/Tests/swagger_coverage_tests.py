"""Toda rota da API aparece no Swagger (/apidocs).

Antes, 12 rotas não apareciam, entre elas as de aprovação por e-mail, o
pedido de mudança e a tela de ofertas: quem revisava não via o contrato."""
import re

import pytest
from mongomock import MongoClient

from configmodule import get_config

FLASGGER = ("/apidocs", "/flasgger", "/apispec", "/static", "/oauth2-redirect.html")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    from SLL import create_app
    return create_app(get_config())


def swagger_path(rule):
    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule)


def test_every_route_is_documented(app):
    documented = app.test_client().get("/apispec_1.json").get_json()["paths"]
    missing = []
    for rule in app.url_map.iter_rules():
        path = str(rule.rule)
        if path.startswith(FLASGGER):
            continue
        methods = {m.lower() for m in rule.methods} - {"head", "options"}
        doc = documented.get(swagger_path(path), {})
        missing += [f"{m.upper()} {path}" for m in sorted(methods) if m not in doc]
    assert missing == []


def test_get_and_post_of_request_changes_have_their_own_docs(app):
    doc = app.test_client().get("/apispec_1.json").get_json()["paths"]["/request_changes"]
    params = lambda m: {p["name"] for p in doc[m].get("parameters", [])}  # noqa: E731
    assert "mudancas" in params("post") and "mudancas" not in params("get")
    assert "400" in doc["post"]["responses"]
