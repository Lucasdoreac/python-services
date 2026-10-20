"""As respostas de erro não revelam o endereço interno do Catálogo nem texto de exceção."""

import requests

from Tests.helpers import OWNER, headers


def test_upstream_failures_do_not_leak_details(client, monkeypatch):
    monkeypatch.setenv("URL_restapi", "http://internal-catalog.hidden/restapi")

    def boom(url, *args, **kwargs):
        if "internal-catalog.hidden" in url:
            raise requests.exceptions.RequestException("could not reach internal-catalog.hidden:5081")
        return True  # a validação de token no Auth

    monkeypatch.setattr("requests.get", boom)
    for path in ("/types", "/courses"):
        response = client.get(path, headers=headers(OWNER))
        assert response.status_code == 502
        assert "internal-catalog" not in response.get_data(as_text=True)
        assert "details" not in response.get_json()


def test_lookup_errors_do_not_echo_the_exception_text(client, monkeypatch):
    from BLL.index import FlowController

    monkeypatch.setenv("URL_restapi", "http://internal-catalog.hidden/restapi")

    def boom(url, *args, **kwargs):
        raise requests.exceptions.RequestException("secret-host.internal refused")

    monkeypatch.setattr("requests.get", boom)
    from flask import Flask

    with Flask(__name__).app_context():
        for call in (lambda: FlowController.find_room_by_id("r1"),
                     lambda: FlowController.find_campus_by_id("c1"),
                     lambda: FlowController.find_types_by_collection("rooms")):
            body, status = call()
            assert status == 400
            assert "secret-host" not in body.get_data(as_text=True)
