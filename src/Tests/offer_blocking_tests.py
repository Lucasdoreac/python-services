import re

import pytest
import requests

from configmodule import get_config

ROOMS = {"data": [{"id": "r1", "name": "101", "campus": "c1"}, {"id": "r2", "name": "102", "campus": "c1"}],
         "pagination": {"page": 1}}
CAMPUS = [{"id": "c1", "name": "Sede"}]

# 23/09/2026 é quarta-feira (ISO 3), 2º semestre.
WEDNESDAY = "2026-09-23"
THURSDAY = "2026-09-24"


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload


def graphql_args(query):
    return dict(re.findall(r"(search\w+):\s*(\d+)", query))


@pytest.fixture
def offers():
    """Ofertas que o internal_apis devolveria; cada teste preenche."""
    return []


@pytest.fixture
def client(monkeypatch, offers):
    # Mongo em memória: conftest.py (mongo_in_memory).
    monkeypatch.setattr('SLL.auth_decorators.token_required', lambda f: f)
    monkeypatch.setenv("URL_restapi", "http://internal/restapi")
    monkeypatch.setenv("URL_graph", "http://internal/graphql/")

    def fake_get(url, params=None, **kwargs):
        return FakeResponse(ROOMS if url.rstrip("/").endswith("rooms") else CAMPUS)

    def fake_post(url, json=None, **kwargs):
        # Imita o filtro do internal_apis: dia da semana, ano e semestre.
        args = graphql_args(json["query"])
        found = [
            {"room": {"id": o["room"]}, "period": {"name": o["period"]}}
            for o in offers
            if "offers" in json["query"]
            and int(args.get("searchWeekday", 0)) in o["weekdays"]
            and int(args.get("searchYear", 0)) == o["year"]
            and int(args.get("searchSemester", 0)) == o["semester"]
        ]
        return FakeResponse({"offers": found})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    from SLL import create_app
    app = create_app(get_config())
    with app.app_context():
        yield app.test_client()


def available(client, date, time):
    response = client.get(f"/rooms/available-rooms?date={date}&time={time}")
    assert response.status_code == 200, response.get_json()
    return [room["id"] for room in response.get_json()["data"]]


def night_class_in_r1(**extra):
    offer = {"room": "r1", "period": "NOITE", "weekdays": [3], "year": 2026, "semester": 2}
    offer.update(extra)
    return offer


def test_room_with_class_at_that_time_is_unavailable(client, offers):
    # python-services #29: antes só a coleção `reservations` era olhada e a
    # sala com aula aparecia livre.
    offers.append(night_class_in_r1())

    assert available(client, WEDNESDAY, "19:30:00") == ["r2"]


def test_search_window_overlapping_the_class_blocks_the_room(client, offers):
    # A busca considera 3 h a partir do horário (mesma janela das reservas).
    offers.append(night_class_in_r1())

    assert available(client, WEDNESDAY, "17:00:00") == ["r2"]


def test_class_only_blocks_its_own_weekday_and_period(client, offers):
    offers.append(night_class_in_r1())

    assert available(client, WEDNESDAY, "08:00:00") == ["r1", "r2"]
    assert available(client, THURSDAY, "19:30:00") == ["r1", "r2"]


def test_offer_from_another_semester_does_not_block(client, offers):
    offers.append(night_class_in_r1(semester=1))

    assert available(client, WEDNESDAY, "19:30:00") == ["r1", "r2"]


def test_unknown_period_does_not_block(client, offers):
    # A carga da planilha grava "não se aplica" quando falta o período.
    offers.append(night_class_in_r1(period="não se aplica"))

    assert available(client, WEDNESDAY, "19:30:00") == ["r1", "r2"]


def test_period_hours_come_from_the_environment(client, offers, monkeypatch):
    from settings import get_offer_settings
    monkeypatch.setenv("OFFER_PERIOD_HOURS", "noite=21:00-22:00")
    get_offer_settings.cache_clear()
    offers.append(night_class_in_r1())
    try:
        assert available(client, WEDNESDAY, "17:00:00") == ["r1", "r2"]
        assert available(client, WEDNESDAY, "20:00:00") == ["r2"]
    finally:
        monkeypatch.delenv("OFFER_PERIOD_HOURS")
        get_offer_settings.cache_clear()


def test_catalog_error_does_not_show_busy_room_as_free(client, monkeypatch):
    # Sem as ofertas não dá para garantir que a sala está livre: falha em vez
    # de mostrar como disponível.
    monkeypatch.setattr(requests, "post", lambda url, json=None, **kw: FakeResponse({"errors": ["boom"]}, 400))

    response = client.get(f"/rooms/available-rooms?date={WEDNESDAY}&time=19:30:00")

    assert response.status_code == 500
