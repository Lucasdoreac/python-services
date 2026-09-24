import pytest
import requests
from mongomock import MongoClient

from configmodule import get_config

CATALOG = {"data": [{"id": "31", "name": "ENFERMAGEM"}, {"id": "39", "name": "DESIGN"}]}
ENFERMAGEM = {"id": 31, "name": "ENFERMAGEM", "coordinator": "coord"}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    monkeypatch.setattr('SLL.auth_decorators.token_required', lambda f: f)
    monkeypatch.setenv("URL_restapi", "http://internal/restapi")

    from SLL import create_app

    calls = []

    def fake_get(url, params=None, **kwargs):
        calls.append((url, params))
        if params and "course_id" in params:
            return FakeResponse(ENFERMAGEM) if str(params["course_id"]) == "31" \
                else FakeResponse({"message": "Course not found"}, 404)
        return FakeResponse(CATALOG)

    monkeypatch.setattr(requests, "get", fake_get)
    app = create_app(get_config())
    with app.app_context():
        test_client = app.test_client()
        test_client.calls = calls
        yield test_client


def test_course_id_returns_that_single_course(client):
    # Antes a rota ignorava course_id e devolvia o catálogo inteiro; o
    # frontend lia course.name num array (undefined) e apagava o curso
    # vinculado ao editar um rascunho (issue #37).
    response = client.get('/courses?course_id=31')

    assert response.status_code == 200
    assert response.get_json() == {"course": ENFERMAGEM}


def test_unknown_course_id_is_404(client):
    response = client.get('/courses?course_id=99999')

    assert response.status_code == 404


def test_search_by_name_still_returns_the_list(client):
    response = client.get('/courses')

    assert response.status_code == 200
    assert response.get_json() == {"courses": CATALOG["data"]}
