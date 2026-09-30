from unittest.mock import Mock

from SLL.email_service import send_email


def test_email_defaults_to_dry_run_without_explicit_configuration(monkeypatch):
    post = Mock(side_effect=AssertionError("default dry-run must not send"))
    monkeypatch.setattr("SLL.email_service.requests.post", post)
    monkeypatch.delenv("EMAIL_DRY_RUN", raising=False)

    response = send_email({"to": ["reviewer@example.test"], "subject": "test"})

    assert response.status_code == 202
    assert response.json() == {"message": "EMAIL_DRY_RUN enabled; email not sent"}
    post.assert_not_called()


def test_email_dry_run_returns_accepted_without_network_call(monkeypatch):
    post = Mock(side_effect=AssertionError("dry-run must not contact sender"))
    monkeypatch.setattr("SLL.email_service.requests.post", post)
    monkeypatch.setenv("EMAIL_DRY_RUN", "TRUE")

    response = send_email({"to": ["reviewer@example.test"], "subject": "test"})

    assert response.status_code == 202
    assert response.json() == {"message": "EMAIL_DRY_RUN enabled; email not sent"}
    post.assert_not_called()


def test_email_is_sent_when_dry_run_is_disabled(monkeypatch):
    post = Mock(return_value=Mock(status_code=200))
    monkeypatch.setattr("SLL.email_service.requests.post", post)
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setenv("CLOUD_FUNCTION_URL", "https://email.example.test")
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "test-key")
    payload = {"to": ["reviewer@example.test"], "subject": "test"}

    response = send_email(payload)

    assert response.status_code == 200
    post.assert_called_once_with(
        "https://email.example.test/send-email",
        json=payload,
        headers={"X-API-Key": "test-key", "Content-Type": "application/json"},
    )
