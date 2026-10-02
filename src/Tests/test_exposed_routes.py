"""Routes that used to answer without credentials now need a user or a signed link."""

import time

import pytest

from DAL import MongoDBConnectionFactory
from SLL import signed_links
from Tests.test_event_submission import OTHER, OWNER, client, create_draft, headers  # noqa: F401


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    monkeypatch.delenv("LINK_SIGNING_KEY", raising=False)  # default: derived from INTERNAL_API_KEY


# --- signed links -----------------------------------------------------------------

def test_a_signed_query_verifies_for_its_event_only():
    query = dict(p.split("=") for p in signed_links.signed_query("evt-1").split("&"))
    assert signed_links.verify("evt-1", query["exp"], query["sig"])
    assert not signed_links.verify("evt-2", query["exp"], query["sig"])


def test_a_tampered_or_expired_link_is_rejected():
    now = time.time()
    query = dict(p.split("=") for p in signed_links.signed_query("evt-1", now=now).split("&"))
    assert not signed_links.verify("evt-1", int(query["exp"]) + 60, query["sig"])
    assert not signed_links.verify("evt-1", query["exp"], query["sig"][:-1] + "0")
    assert not signed_links.verify("evt-1", query["exp"], "")
    assert not signed_links.verify("evt-1", "not-a-number", query["sig"])
    assert not signed_links.verify("evt-1", None, None)
    assert not signed_links.verify("evt-1", query["exp"], query["sig"], now=now + signed_links.ttl_seconds() + 1)


def test_the_default_key_is_derived_from_the_internal_key(monkeypatch):
    query = dict(p.split("=") for p in signed_links.signed_query("evt-1").split("&"))
    assert signed_links.verify("evt-1", query["exp"], query["sig"])
    monkeypatch.setenv("INTERNAL_API_KEY", "a-rotated-internal-key")
    assert not signed_links.verify("evt-1", query["exp"], query["sig"])  # old links stop working


def test_the_internal_key_itself_is_not_the_signing_key(monkeypatch):
    import hashlib, hmac

    monkeypatch.setenv("INTERNAL_API_KEY", "internal-key")
    exp = int(time.time()) + 100
    naive = hmac.new(b"internal-key", f"pdf:evt-1:{exp}".encode(), hashlib.sha256).hexdigest()
    assert not signed_links.verify("evt-1", exp, naive)


def test_an_explicit_signing_key_overrides_the_derived_one(monkeypatch):
    query = dict(p.split("=") for p in signed_links.signed_query("evt-1").split("&"))
    monkeypatch.setenv("LINK_SIGNING_KEY", "an-explicit-key")
    assert not signed_links.verify("evt-1", query["exp"], query["sig"])
    fresh = dict(p.split("=") for p in signed_links.signed_query("evt-1").split("&"))
    assert signed_links.verify("evt-1", fresh["exp"], fresh["sig"])


def test_no_key_at_all_means_nothing_verifies(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    assert not signed_links.verify("evt-1", int(time.time()) + 100, "0" * 64)


# --- the PDF route ----------------------------------------------------------------

def store_pdf(event_id):
    MongoDBConnectionFactory.get_db().pdfs.insert_one(
        {"eventId": event_id, "content": b"%PDF-1.4 test", "contentType": "application/pdf", "filename": "e.pdf"}
    )


def test_pdf_needs_a_signed_link(client):
    event_id = create_draft(client)
    store_pdf(event_id)
    assert client.get(f"/events/{event_id}/pdf").status_code == 403
    assert client.get(f"/events/{event_id}/pdf?exp=9999999999&sig=abc").status_code == 403
    other = create_draft(client)
    wrong = signed_links.signed_query(other)
    assert client.get(f"/events/{event_id}/pdf?{wrong}").status_code == 403


def test_pdf_opens_with_a_valid_link_and_is_not_cached_publicly(client):
    event_id = create_draft(client)
    store_pdf(event_id)
    response = client.get(f"/events/{event_id}/pdf?{signed_links.signed_query(event_id)}")
    assert response.status_code == 200 and response.data.startswith(b"%PDF")
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_the_e_mail_link_carries_the_signature(monkeypatch):
    from BLL.send_emails import _pdf_link

    monkeypatch.delenv("MINIO_URL", raising=False)
    monkeypatch.setenv("SERVER_NAME", "api.example.test")
    monkeypatch.setenv("SERVER_SCHEME", "https")
    link = _pdf_link("evt-9")
    assert link.startswith("https://api.example.test/events/evt-9/pdf?exp=")
    query = dict(p.split("=") for p in link.split("?")[1].split("&"))
    assert signed_links.verify("evt-9", query["exp"], query["sig"])


# --- reservations by date and notify_reservation -------------------------------------

def test_reservations_by_date_needs_a_user_token(client):
    assert client.get("/reservations/2031-03-01").status_code == 401
    assert client.get("/reservations/2031-03-01", headers=headers(OWNER)).status_code in (200, 404)


def test_notify_reservation_needs_a_token_and_the_organizer(client, monkeypatch):
    event_id = create_draft(client)
    assert client.get(f"/notify_reservation?eventId={event_id}").status_code == 401
    assert client.get(f"/notify_reservation?eventId={event_id}", headers=headers(OTHER)).status_code == 403
    assert client.get("/notify_reservation?eventId=000000000000000000000000",
                      headers=headers(OWNER)).status_code == 404

    calls = []

    class Sent:
        status_code = 200

    monkeypatch.setattr("SLL.administration_approval.send_reservation_info_to_reitoria",
                        lambda event_id: calls.append(event_id) or Sent())
    monkeypatch.delenv("FLASK_ENV", raising=False)
    ok = client.get(f"/notify_reservation?eventId={event_id}", headers=headers(OWNER))
    assert ok.status_code == 200 and calls == [event_id]


# --- error details ------------------------------------------------------------------

def test_upstream_failures_do_not_leak_details(client, monkeypatch):
    import requests

    monkeypatch.setenv("URL_restapi", "http://internal-catalog.hidden/restapi")

    def boom(url, *args, **kwargs):
        if "internal-catalog.hidden" in url:
            raise requests.exceptions.RequestException("could not reach internal-catalog.hidden:5081")
        return True  # the Auth check

    monkeypatch.setattr("requests.get", boom)
    for path in ("/types", "/courses"):
        response = client.get(path, headers=headers(OWNER))
        assert response.status_code == 502
        assert "internal-catalog" not in response.get_data(as_text=True)
        assert "details" not in response.get_json()
