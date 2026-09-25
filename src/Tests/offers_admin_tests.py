"""Tela de ofertas (item 5 do backlog): quem está em OFFER_ADMIN_EMAILS marca os
dias da semana das ofertas (aulas do semestre). Sem dia, a aula não bloqueia
sala (#29); as ofertas vêm da planilha da UDF sem essa informação.

Lista vazia (padrão) = ninguém tem acesso."""
import pytest
from mongomock import MongoClient

from configmodule import get_config

ADMIN = "secretaria@udf.edu.br"
OFFER = {"id": "o1", "offerId": 10, "weekdays": [], "discipline": {"name": "CÁLCULO I"},
         "period": {"name": "NOITE"}, "room": {"name": "101"}, "teacher": {"name": "Prof. X"},
         "campus": {"name": "SEDE"}}


class Ok:
    status_code = 200
    def __bool__(self): return True


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    # token_required consulta o auth_service: aqui qualquer token vale
    monkeypatch.setattr('SLL.auth_decorators.requests.get', lambda *a, **k: Ok())
    monkeypatch.setenv("OFFER_ADMIN_EMAILS", f" {ADMIN.upper()} , outra@udf.edu.br")
    from settings import get_offer_settings
    get_offer_settings.cache_clear()
    from SLL import create_app
    app = create_app(get_config())
    with app.app_context():
        yield app.test_client()
    get_offer_settings.cache_clear()


@pytest.fixture
def catalog(monkeypatch):
    from SLL.cluster_api.request_methods import GraphQlRequestMethods, RestApiRequestMethods
    calls = {}

    def page(**kw):
        calls["page"] = kw
        return [OFFER]

    def patch(offer_id, weekdays):
        calls["patch"] = (offer_id, weekdays)
        return 200, {**OFFER, "id": offer_id, "weekdays": weekdays}

    monkeypatch.setattr(GraphQlRequestMethods, "get_offers_page", staticmethod(page))
    monkeypatch.setattr(RestApiRequestMethods, "set_offer_weekdays", staticmethod(patch))
    return calls


def h(email):
    return {"email": email, "token": "t"}


def test_permissions_tell_the_front_who_sees_the_screen(client):
    assert client.get("/auth/permissions", headers=h(ADMIN)).get_json() == {"manageOffers": True}
    assert client.get("/auth/permissions", headers=h("prof@udf.edu.br")).get_json() == {"manageOffers": False}


def test_list_offers_for_admin(client, catalog):
    res = client.get("/offers/manage?year=2024&semester=2&discipline=calc&page=2", headers=h(ADMIN))
    assert res.status_code == 200
    body = res.get_json()
    assert body["offers"][0]["discipline"] == "CÁLCULO I"
    assert body["offers"][0]["weekdays"] == []
    assert catalog["page"] == {"year": 2024, "semester": 2, "discipline": "calc", "first": 20, "skip": 20}


def test_set_weekdays_for_admin(client, catalog):
    res = client.put("/offers/o1/weekdays", json={"weekdays": [3, 1]}, headers=h(ADMIN))
    assert res.status_code == 200
    assert catalog["patch"] == ("o1", [3, 1])
    assert res.get_json()["weekdays"] == [3, 1]


@pytest.mark.parametrize("call", [
    lambda c: c.get("/offers/manage", headers=h("prof@udf.edu.br")),
    lambda c: c.put("/offers/o1/weekdays", json={"weekdays": [1]}, headers=h("prof@udf.edu.br")),
])
def test_anyone_else_gets_403_and_catalog_is_not_touched(client, catalog, call):
    assert call(client).status_code == 403
    assert catalog == {}


def test_without_login_is_401(client, catalog):
    assert client.get("/offers/manage").status_code == 401


def test_nobody_has_access_by_default(monkeypatch):
    monkeypatch.delenv("OFFER_ADMIN_EMAILS", raising=False)
    from settings import OfferSettings
    assert OfferSettings().can_manage_offers(ADMIN) is False
