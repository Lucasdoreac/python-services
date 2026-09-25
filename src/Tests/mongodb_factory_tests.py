"""MongoDBConnectionFactory: um MongoClient por processo, criado no init_app.

Substitui o antigo Tests/dal.py, que o pytest nunca coletava (nome fora do
padrão) e testava uma API que não existe mais (DAL.index.load_variables)."""
import mongomock
import pytest

from DAL import mongodb_factory
from DAL.mongodb_factory import MongoDBConnectionFactory


@pytest.fixture
def fresh_factory(monkeypatch):
    # O conftest já injeta um cliente; aqui a fábrica começa vazia.
    monkeypatch.setattr(MongoDBConnectionFactory, "_client", None)
    monkeypatch.setattr(MongoDBConnectionFactory, "_database", None)
    monkeypatch.setattr(mongodb_factory, "MongoClient", mongomock.MongoClient)


def test_get_db_before_init_app_fails_loudly(fresh_factory):
    with pytest.raises(Exception, match="has not been initialized"):
        MongoDBConnectionFactory.get_db()


def test_init_app_selects_the_database(fresh_factory):
    MongoDBConnectionFactory.init_app("mongodb://localhost:27017/", "test_db")
    assert MongoDBConnectionFactory.get_db().name == "test_db"


def test_single_client_even_if_init_app_runs_twice(fresh_factory):
    MongoDBConnectionFactory.init_app("mongodb://localhost:27017/", "test_db")
    first = MongoDBConnectionFactory.get_db().client
    MongoDBConnectionFactory.init_app("mongodb://outro:27017/", "outro_db")
    assert MongoDBConnectionFactory.get_db().client is first
    assert MongoDBConnectionFactory.get_db().name == "test_db"


def test_reads_back_what_it_writes(fresh_factory):
    MongoDBConnectionFactory.init_app("mongodb://localhost:27017/", "test_db")
    db = MongoDBConnectionFactory.get_db()
    db["test_collection"].insert_one({"name": "test_item"})
    assert db["test_collection"].count_documents({}) == 1
