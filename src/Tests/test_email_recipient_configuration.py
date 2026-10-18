import pytest
from mongomock import MongoClient

from DAL import MongoDBConnectionFactory


@pytest.fixture
def load_recipients(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    monkeypatch.setattr(MongoDBConnectionFactory, "_client", MongoClient())
    monkeypatch.setattr(MongoDBConnectionFactory, "_database", "email_recipient_config_test")
    from BLL.send_emails import load_email_recipients

    return load_email_recipients


def test_development_defaults_are_preserved_without_overrides(load_recipients):
    recipients = load_recipients({"FLASK_ENV": "development"})

    assert recipients == {
        "reitoria": ["danrleywillian@gmail.com", "guilherme.amaral2004@gmail.com"],
        "coordenacao": ["dwcorpbrasil@gmail.com", "danrley.pereira@cs.udf.edu.br"],
    }


def test_explicit_environment_lists_override_development_defaults(load_recipients):
    recipients = load_recipients({
        "FLASK_ENV": "development",
        "EMAIL_RECIPIENTS_REITORIA": "Test.Reitoria@example.test, lucas@example.test, test.reitoria@example.test",
        "EMAIL_RECIPIENTS_COORDENACAO": "Test.Coordenacao@example.test, lucas@example.test",
    })

    assert recipients["reitoria"] == ["test.reitoria@example.test", "lucas@example.test"]
    assert recipients["coordenacao"] == ["test.coordenacao@example.test", "lucas@example.test"]


def test_explicit_empty_override_fails_closed_and_keeps_production_default(load_recipients):
    recipients = load_recipients({
        "FLASK_ENV": "production",
        "EMAIL_RECIPIENTS_REITORIA": " , ",
        "EMAIL_RECIPIENTS_COORDENACAO": "",
    })

    assert recipients["reitoria"] == []
    assert recipients["coordenacao"] == []
    assert recipients["reservas"] == ["bruno.silva@udf.edu.br"]


def test_production_defaults_are_preserved_without_overrides(load_recipients):
    recipients = load_recipients({"FLASK_ENV": "production"})

    assert recipients["reitoria"] == ["suelaine.santos@udf.edu.br"]
    assert recipients["coordenacao"] == []
