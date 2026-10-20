"""A API envia x-api-key ao Catálogo somente quando INTERNAL_API_KEY está configurada."""

from SLL.cluster_api.request_methods import GraphQlRequestMethods, RestApiRequestMethods


class Ok:
    status_code = 200

    def json(self):
        return {"data": {}}


def capture_headers(monkeypatch):
    seen = []
    monkeypatch.setattr("SLL.cluster_api.request_methods.requests.get",
                        lambda url, **kw: seen.append(kw.get("headers")) or Ok())
    monkeypatch.setattr("SLL.cluster_api.request_methods.requests.post",
                        lambda url, **kw: seen.append(kw.get("headers")) or Ok())
    monkeypatch.setenv("URL_restapi", "https://catalog.test/restapi")
    monkeypatch.setenv("URL_graph", "https://catalog.test/graphql/")
    return seen


def test_without_the_key_no_header_is_added(monkeypatch):
    seen = capture_headers(monkeypatch)
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)

    RestApiRequestMethods.get_request_simple("https://catalog.test/restapi/rooms/")
    GraphQlRequestMethods.get_all_campus_request()

    assert seen == [{}, {}]


def test_with_the_key_every_catalog_call_carries_it(monkeypatch):
    seen = capture_headers(monkeypatch)
    monkeypatch.setenv("INTERNAL_API_KEY", "catalog-key")

    RestApiRequestMethods.get_request_simple("https://catalog.test/restapi/rooms/")
    RestApiRequestMethods.get_request_with_params("https://catalog.test/restapi/rooms/", {"a": 1})
    RestApiRequestMethods.get_request_page("https://catalog.test/restapi/rooms/", 1, 10)
    GraphQlRequestMethods.get_all_campus_request()
    GraphQlRequestMethods.get_all_periods_request()

    assert seen == [{"x-api-key": "catalog-key"}] * 5
