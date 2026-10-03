"""Each recipient reaches /send-email as its own address, never as one comma-joined string.

The endpoint (and Brevo behind it) takes a list; a single "a@x, b@x" text is one invalid address, so with
two or more recipients nothing was delivered. These tests run the real send_email() against a fake
requests.post and look at the JSON the provider-facing service receives.
"""
import pytest
from bson import ObjectId
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory
from SLL import create_app

TWO = ["first@example.test", "second@example.test"]


@pytest.fixture
def mail(monkeypatch):
    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    MongoDBConnectionFactory._client = MongoClient()
    MongoDBConnectionFactory._database = "email_recipients_test"
    import BLL.index as bll_index
    import BLL.send_emails as send_emails
    from DAL.collections_repositories import EventsRepository, SendEmailrepository

    bll_index.events_repository = EventsRepository()
    send_emails.events_repository = bll_index.events_repository
    send_emails.send_email_repository = SendEmailrepository()

    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setenv("CLOUD_FUNCTION_URL", "http://cloud-function.test")
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "test-function-key")
    sent = []

    def post(url, json=None, headers=None):
        sent.append({"url": url, "json": json})

        class Response:
            status_code = 200

        return Response()

    monkeypatch.setattr("SLL.email_service.requests.post", post)
    monkeypatch.setitem(send_emails.emails, "coordenacao", list(TWO))
    monkeypatch.setitem(send_emails.emails, "reitoria", list(TWO))
    monkeypatch.setattr(send_emails.FlowController, "find_event_by_event_id",
                        lambda _id: {"graduationId": "course-1", "organizer": {"email": "owner@example.test"}})
    monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda _id: None)

    app = create_app(get_config())
    with app.app_context():
        db = MongoDBConnectionFactory.get_db()
        event_id = str(ObjectId())
        db.events.insert_one({
            "_id": ObjectId(event_id), "status": "waiting",
            "approvalTokenGroups": {"0": "g0", "1": "g1"},
            "organizer": {"email": "owner@example.test"},
        })
        db.reservations.insert_one({"eventId": event_id, "roomId": "room-1", "status": "waiting"})
        yield send_emails, event_id, sent


def delivered(sent):
    assert len(sent) == 1, sent
    assert sent[0]["url"] == "http://cloud-function.test/send-email"
    return sent[0]["json"]["to"]


def test_coordenacao_with_two_recipients_sends_two_addresses(mail):
    send_emails, event_id, sent = mail
    send_emails.send_to_coordenacao(event_id)
    assert delivered(sent) == TWO


def test_reitoria_approval_with_two_recipients_sends_two_addresses(mail):
    send_emails, event_id, sent = mail
    MongoDBConnectionFactory.get_db().events.update_one(
        {"_id": ObjectId(event_id)}, {"$set": {"status": "approved_by_coordenacao"}})
    send_emails.send_to_reitoria(event_id)
    assert delivered(sent) == TWO


def test_reservation_notice_with_two_recipients_sends_two_addresses(mail):
    send_emails, event_id, sent = mail
    send_emails.send_reservation_info_to_reitoria(event_id)
    assert delivered(sent) == TWO


def test_a_single_recipient_is_still_a_list_of_one(mail, monkeypatch):
    send_emails, event_id, sent = mail
    monkeypatch.setitem(send_emails.emails, "reitoria", [TWO[0]])
    send_emails.send_reservation_info_to_reitoria(event_id)
    assert delivered(sent) == [TWO[0]]
