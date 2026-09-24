import sys

import mongomock
import pytest

# Módulos de rota que aplicam @token_required NA IMPORTAÇÃO. Os testes trocam
# SLL.auth_decorators.token_required antes de criar o app, mas o Python só
# importa um módulo uma vez: quem criava o app primeiro decidia para todos, e
# a suíte só passava na ordem da lista do run-tests.sh. Descartá-los antes de
# cada teste faz o create_app reimportar com o decorator que o teste escolheu.
ROUTE_MODULES = (
    "SLL.auth_routes", "SLL.events_routes", "SLL.reservation_routes",
    "SLL.types_routes", "SLL.resource_routes", "SLL.administration_approval",
)


@pytest.fixture(autouse=True)
def fresh_route_modules():
    for name in ROUTE_MODULES:
        sys.modules.pop(name, None)
    yield


# Um único Mongo em memória para a suíte toda: repositórios criados na
# importação (ex.: em BLL.send_emails) guardam o cliente do primeiro uso, então
# um cliente novo por teste separaria escrita e leitura.
MONGO = mongomock.MongoClient()


@pytest.fixture(autouse=True)
def mongo_in_memory(monkeypatch):
    # MongoDBConnectionFactory liga o MongoClient na importação do módulo e
    # guarda o cliente na classe: dependendo de qual teste importava primeiro,
    # a suíte usava mongomock ou um Mongo real inexistente (timeouts de 30 s).
    from DAL import MongoDBConnectionFactory
    monkeypatch.setattr(MongoDBConnectionFactory, "_client", MONGO)
    monkeypatch.setattr(MongoDBConnectionFactory, "_database", "test")
