from unittest.mock import Mock

from flask import Response
from mongomock import MongoClient

from SLL.email_policy import is_email_allowed


def test_allows_base_udf_domain():
    assert is_email_allowed("user@udf.edu.br")


def test_allows_exact_staging_allowlist_address():
    assert is_email_allowed(
        "Lucas.Dorea@cs.udf.edu.br",
        "lucas.dorea@cs.udf.edu.br,kerlla.luz@udf.edu.br",
    )


def test_does_not_allow_unlisted_subdomain_address():
    assert not is_email_allowed("other@cs.udf.edu.br")


def test_rejects_malformed_email():
    assert not is_email_allowed("@udf.edu.br")


def test_auth_route_forwards_an_explicitly_allowed_developer_email(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    import configmodule
    from SLL import create_app

    monkeypatch.setattr(configmodule.Config, "MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setattr(configmodule.Config, "MONGO_DATABASE", "labtech_test")
    app = create_app(configmodule.get_config())
    from SLL.auth_routes import AuthRoutes

    insert_token = Mock(return_value=Response("accepted", status=202))
    monkeypatch.setattr(
        "SLL.auth_routes.AuthenticationController.insert_token", insert_token
    )
    monkeypatch.setenv(
        "AUTH_EMAIL_ALLOWLIST", "lucas.dorea@cs.udf.edu.br,kerlla.luz@udf.edu.br"
    )
    with app.test_request_context(
        "/auth/send-link?email=lucas.dorea%40cs.udf.edu.br", method="POST"
    ):
        response = AuthRoutes.auth_mail()

    assert response.status_code == 202
    insert_token.assert_called_once_with("lucas.dorea@cs.udf.edu.br")
