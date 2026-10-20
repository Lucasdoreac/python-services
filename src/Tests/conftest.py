"""Fixtures compartilhadas: aplicação Flask com Mongo em memória (mongomock) e Auth simulado.

Nenhum teste abre conexão de rede: o Auth responde "válido" por substituição de
``requests.get`` e o Mongo é o mongomock.
"""

from types import SimpleNamespace

import pytest
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory
from SLL import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    MongoDBConnectionFactory._client = MongoClient()
    MongoDBConnectionFactory._database = "labtech_test"
    MongoDBConnectionFactory._client.drop_database("labtech_test")  # o mongomock compartilha o armazenamento entre clientes
    import BLL.index as bll_index
    from DAL import (
        BuildingsRepository,
        ReservationsRepository,
        RoomsRepository,
        TypesRepository,
        UniversityRepository,
    )

    bll_index.university_repository = UniversityRepository()
    bll_index.buildings_repository = BuildingsRepository()
    bll_index.rooms_repository = RoomsRepository()
    bll_index.types_repository = TypesRepository()
    bll_index.reservations_repository = ReservationsRepository()
    bll_index.events_repository = bll_index.EventsRepository()
    import BLL.send_emails as send_emails
    from DAL.collections_repositories import SendEmailrepository

    send_emails.events_repository = bll_index.events_repository
    send_emails.send_email_repository = SendEmailrepository()
    monkeypatch.setattr("SLL.auth_decorators.requests.get", lambda *args, **kwargs: True)
    app = create_app(get_config())
    # Substitui o módulo `pdf` só dentro de events_routes, sem trocar a função real de BLL.pdf.
    monkeypatch.setattr("SLL.events_routes.pdf", SimpleNamespace(generate_event_pdf=lambda **kwargs: None))
    monkeypatch.setattr("SLL.events_routes.send_to_coordenacao", lambda **kwargs: None)
    monkeypatch.setattr("SLL.events_routes.send_reservation_info_to_reitoria", lambda **kwargs: None)
    with app.app_context():
        yield app.test_client()
