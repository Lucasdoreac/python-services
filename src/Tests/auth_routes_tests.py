import pytest
from mongomock import MongoClient

from configmodule import get_config


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    monkeypatch.delenv("AUTH_ALLOWED_DOMAIN", raising=False)
    monkeypatch.delenv("AUTH_ALLOWED_EMAILS", raising=False)

    from SLL import create_app
    from settings import get_auth_settings

    get_auth_settings.cache_clear()
    app = create_app(get_config())

    sent = []
    from BLL import AuthenticationController
    monkeypatch.setattr(
        AuthenticationController,
        "insert_token",
        lambda self, email: sent.append(email) or ({"ok": True}, 200),
    )
    with app.app_context():
        test_client = app.test_client()
        test_client.sent = sent
        yield test_client
    get_auth_settings.cache_clear()


def post_link(client, email=None):
    return client.post('/auth/send-link', query_string={"email": email} if email is not None else {})


def test_institutional_domain_gets_a_link(client):
    response = post_link(client, "aluno@udf.edu.br")

    assert response.status_code == 200
    assert client.sent == ["aluno@udf.edu.br"]


def test_other_domain_is_rejected(client):
    response = post_link(client, "alguem@gmail.com")

    assert response.status_code == 400
    assert client.sent == []


def test_missing_email_is_400_not_500(client):
    # Antes: email.endswith(...) em None -> AttributeError -> 500.
    response = post_link(client)

    assert response.status_code == 400
    assert client.sent == []


def test_domain_trick_with_two_at_signs_is_rejected(client):
    response = post_link(client, "atacante@evil.com@udf.edu.br")

    assert response.status_code == 400
    assert client.sent == []


def test_previously_hardcoded_exception_is_no_longer_in_code(client):
    # danrley.pereira@cs.udf.edu.br era uma exceção fixa em auth_routes.py.
    response = post_link(client, "danrley.pereira@cs.udf.edu.br")

    assert response.status_code == 400


def test_extra_allowed_emails_come_from_environment(client, monkeypatch):
    from settings import get_auth_settings

    monkeypatch.setenv("AUTH_ALLOWED_EMAILS", "parceiro@dwcorp.com.br, outro@ex.com")
    get_auth_settings.cache_clear()

    assert post_link(client, "parceiro@dwcorp.com.br").status_code == 200
    assert post_link(client, "Outro@Ex.com").status_code == 200
    assert client.sent == ["parceiro@dwcorp.com.br", "Outro@Ex.com"]


def test_allowed_domain_is_configurable(client, monkeypatch):
    from settings import get_auth_settings

    monkeypatch.setenv("AUTH_ALLOWED_DOMAIN", "outra.edu.br")
    get_auth_settings.cache_clear()

    assert post_link(client, "x@outra.edu.br").status_code == 200
    assert post_link(client, "x@udf.edu.br").status_code == 400
