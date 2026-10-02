import pytest


@pytest.fixture(autouse=True)
def internal_api_key(monkeypatch):
    """create_app refuses to start without the Catalog key; tests hold a fake one."""
    monkeypatch.setenv("INTERNAL_API_KEY", "test-internal-key")
