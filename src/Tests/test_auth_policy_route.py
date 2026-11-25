from flask import Response


def test_missing_email_is_rejected_without_contacting_auth(client, monkeypatch):
    calls = []
    monkeypatch.setattr('SLL.auth_routes.AuthenticationController.insert_token', lambda self, email: calls.append(email))
    response = client.post('/auth/send-link')
    assert response.status_code == 400
    assert calls == []


def test_default_exception_and_udf_address_are_forwarded(client, monkeypatch):
    monkeypatch.delenv('AUTH_EMAIL_ALLOWLIST', raising=False)
    calls = []
    monkeypatch.setattr('SLL.auth_routes.AuthenticationController.insert_token', lambda self, email: calls.append(email) or Response(status=202))
    for email in ('pessoa@udf.edu.br', 'danrley.pereira@cs.udf.edu.br'):
        assert client.post('/auth/send-link', query_string={'email': email}).status_code == 202
    assert calls == ['pessoa@udf.edu.br', 'danrley.pereira@cs.udf.edu.br']


def test_allowlist_is_exact_and_override_is_explicit(client, monkeypatch):
    monkeypatch.setenv('AUTH_EMAIL_ALLOWLIST', 'allow@cs.udf.edu.br')
    calls = []
    monkeypatch.setattr('SLL.auth_routes.AuthenticationController.insert_token', lambda self, email: calls.append(email) or Response(status=202))
    assert client.post('/auth/send-link', query_string={'email': 'allow@cs.udf.edu.br'}).status_code == 202
    for email in ('danrley.pereira@cs.udf.edu.br', '@udf.edu.br', 'a@udf.edu.br.evil.test', 'a@@udf.edu.br'):
        assert client.post('/auth/send-link', query_string={'email': email}).status_code == 400
    assert calls == ['allow@cs.udf.edu.br']
