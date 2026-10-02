from types import SimpleNamespace

import pytest

from SLL import client_limits

CLIENT = "203.0.113.7"
FORGED = "198.51.100.99"


def fake_request(headers=None, remote_addr="127.0.0.1"):
    return SimpleNamespace(headers=headers or {}, remote_addr=remote_addr)


@pytest.fixture(autouse=True)
def default_hops(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)


def test_platform_header_wins_over_forwarded_for():
    request = fake_request(
        {"True-Client-IP": CLIENT, "X-Forwarded-For": f"{CLIENT}, 10.0.0.1, 10.0.0.2"}
    )
    assert client_limits.client_ip(request) == CLIENT


def test_forged_leftmost_forwarded_entry_is_never_chosen_with_platform_header():
    request = fake_request(
        {
            "True-Client-IP": CLIENT,
            "X-Forwarded-For": f"{FORGED}, {CLIENT}, 10.0.0.1, 10.0.0.2",
        }
    )
    assert client_limits.client_ip(request) == CLIENT


def test_ipv6_platform_header_is_accepted():
    request = fake_request({"True-Client-IP": " 2001:db8::1 "})
    assert client_limits.client_ip(request) == "2001:db8::1"


@pytest.mark.parametrize("value", ["not-an-ip", "", "   ", "1.2.3.4, 5.6.7.8", "9" * 100])
def test_invalid_platform_header_is_ignored_and_forwarded_rule_applies(value):
    request = fake_request(
        {"True-Client-IP": value, "X-Forwarded-For": f"{CLIENT}, 10.0.0.1"}
    )
    assert client_limits.client_ip(request) == "10.0.0.1"


def test_forwarded_rule_uses_configured_hops(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "3")
    request = fake_request({"X-Forwarded-For": f"{FORGED}, {CLIENT}, 10.0.0.1, 10.0.0.2"})
    assert client_limits.client_ip(request) == CLIENT


def test_no_headers_uses_remote_addr():
    assert client_limits.client_ip(fake_request(remote_addr="127.0.0.1")) == "127.0.0.1"


def test_nothing_known_is_unknown():
    assert client_limits.client_ip(fake_request(remote_addr=None)) == "unknown"
