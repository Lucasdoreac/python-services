import ast
import pathlib

import pytest
import requests

from configmodule import get_config

SRC = pathlib.Path(__file__).resolve().parents[1]
# Chamadas HTTP que NÃO vão para o catálogo (auth_service e envio de e-mail).
NOT_CATALOG = {"BLL/authentication.py", "SLL/auth_decorators.py", "SLL/email_service.py",
               "BLL/send_emails.py", "SLL/sendblue.py"}


def test_every_catalog_call_sends_the_api_key():
    # O catálogo passou a exigir x-api-key em tudo (shared-resources SEC-04).
    # Qualquer requests.get/post novo que esqueça a chave quebra aqui, não em produção.
    missing = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        if rel.startswith("Tests/") or rel in NOT_CATALOG:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and ast.unparse(node.func) in ("requests.get", "requests.post"):
                headers = [k for k in node.keywords if k.arg == "headers"]
                if not headers or ast.unparse(headers[0].value) != "catalog_headers()":
                    missing.append(f"{rel}:{node.lineno}")
    assert missing == []


@pytest.fixture
def calls(monkeypatch):
    # Mongo em memória: conftest.py (mongo_in_memory).
    monkeypatch.setattr('SLL.auth_decorators.token_required', lambda f: f)
    monkeypatch.setenv("URL_restapi", "http://internal/restapi")
    monkeypatch.setenv("URL_graph", "http://internal/graphql/")
    monkeypatch.setenv("INTERNAL_API_KEY", "chave-do-reservas")
    seen = []

    class Response:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

        def raise_for_status(self):
            pass

    def fake_get(url, params=None, headers=None, **kwargs):
        seen.append((url, headers))
        return Response({"data": [], "pagination": {}} if "rooms" in url or "courses" in url else [])

    def fake_post(url, json=None, headers=None, **kwargs):
        seen.append((url, headers))
        return Response({"offers": []})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)
    from SLL import create_app
    app = create_app(get_config())
    with app.app_context():
        yield app.test_client(), seen


def test_room_search_and_courses_send_the_key_to_the_catalog(calls):
    client, seen = calls

    client.get("/rooms/available-rooms?date=2026-09-23&time=19:30:00")
    client.get("/courses?course_name=ENF")

    assert seen, "nenhuma chamada ao catálogo foi feita"
    assert [(url, h) for url, h in seen if (h or {}).get("x-api-key") != "chave-do-reservas"] == []
