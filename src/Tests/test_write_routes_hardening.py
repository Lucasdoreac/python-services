"""POST /reservations is gone, and client text never reaches the Typst source."""

import json

import pytest
import typst

from DAL import MongoDBConnectionFactory
from Tests.test_event_submission import OWNER, client, headers, slot  # noqa: F401

PAYLOAD = '`]#panic("injected")[`#read("/etc/hostname")*_$ [ ] ` ``` #include "x.typ"'


def event_document(**overrides):
    event = {
        "name": "Event",
        "organizer": {"name": "Org", "email": "org.name@udf.edu.br", "phone": "61 99999-0000"},
        "eventTypeId": "lecture",
        "odsId": "1",
        "description": "Descrição normal",
        "graduationId": "12",
        "targetPublic": ["Alunos"],
        "resources": ["Projetor"],
        "expectedSubscribers": "30",
        "roomType": "auditorio",
        "entrepreneuralPath": "",
        "extensionProject": "",
        "studentsMonitors": ["Ana"],
    }
    event.update(overrides)
    return event


@pytest.fixture
def pdf(monkeypatch):
    """BLL.pdf, imported once a (mongomock) connection factory exists.

    Not the ``client`` fixture: that one replaces generate_event_pdf with a stub.
    """
    from mongomock import MongoClient

    monkeypatch.setattr("pymongo.MongoClient", MongoClient)
    monkeypatch.setattr("DAL.mongodb_factory.MongoClient", MongoClient)
    MongoDBConnectionFactory._client = MongoClient()
    MongoDBConnectionFactory._database = "labtech_test"
    from BLL import pdf as module

    return module


@pytest.fixture
def render(monkeypatch, pdf):
    """Run generate_event_pdf with the Typst compiler wrapped to record its inputs."""
    seen = {}

    def run(event):
        monkeypatch.setattr(pdf.FlowController, "find_types_by_collection",
                            staticmethod(lambda collection: {"types": [{"id": "1", "name": "Educação de qualidade"}]}))
        monkeypatch.setattr(pdf.FlowController, "find_event_by_event_id", staticmethod(lambda event_id: event))
        monkeypatch.setattr(pdf.FlowController, "find_reservation_by_event_id", staticmethod(lambda event_id: []))
        monkeypatch.setattr(pdf, "save_pdf", lambda event_id, path: seen.update(pdf=open(path, "rb").read()))
        real = typst.compile

        def spy(path, *args, **kwargs):
            seen["typ"] = open(path, encoding="utf-8").read()
            seen["data"] = json.load(open(path.replace("evento.typ", "data.json"), encoding="utf-8"))
            return real(path, *args, **kwargs)

        monkeypatch.setattr(pdf.typst, "compile", spy)
        pdf.generate_event_pdf("evt-1")
        return seen

    return run


def test_a_normal_event_still_compiles_to_a_pdf(render):
    seen = render(event_document())
    assert seen["pdf"].startswith(b"%PDF")
    assert seen["data"]["description"] == "Descrição normal"
    assert seen["data"]["organizer_email"] == "org.name@udf.edu.br"
    assert seen["data"]["organizer_name"] == "org.name"
    assert seen["data"]["ods"] == "Educação de qualidade"


def test_markup_in_every_field_is_data_not_source(render):
    fields = {k: PAYLOAD for k in ("description", "graduationId", "eventTypeId", "roomType", "expectedSubscribers")}
    event = event_document(**fields, organizer={"name": PAYLOAD, "email": PAYLOAD + "@udf.edu.br", "phone": PAYLOAD},
                           targetPublic=[PAYLOAD], resources=[PAYLOAD], studentsMonitors=[PAYLOAD],
                           entrepreneuralPath=PAYLOAD, extensionProject=PAYLOAD)
    seen = render(event)
    assert seen["pdf"].startswith(b"%PDF"), "the PDF must still build with hostile text"
    for fragment in ("panic", "injected", "/etc/hostname", "include", "```"):
        assert fragment not in seen["typ"], f"client text reached the Typst source: {fragment}"
    assert PAYLOAD[:40] in seen["data"]["description"]
    assert PAYLOAD[:40] in seen["data"]["organizer_phone"]


def test_field_lengths_are_capped(render, pdf):
    seen = render(event_document(description="x" * 50000, graduationId="y" * 5000))
    assert len(seen["data"]["description"]) == pdf.PDF_FIELD_LIMIT
    assert len(seen["data"]["course"]) == pdf.PDF_SHORT_FIELD_LIMIT


def test_missing_values_become_empty_text_not_the_word_none(render):
    seen = render(event_document(odsId="999"))
    assert seen["data"]["ods"] == ""


def test_post_reservations_no_longer_exists(client):
    before = MongoDBConnectionFactory.get_db().reservations.count_documents({})
    body = {"roomId": "any-room", "reservationDate": slot()["reservationDate"], "eventId": "someone-elses-event"}
    response = client.post("/reservations", json=body, headers=headers(OWNER))
    assert response.status_code in (404, 405)
    assert MongoDBConnectionFactory.get_db().reservations.count_documents({}) == before


def test_reading_reservations_still_works(client):
    assert client.get("/reservations?eventId=none", headers=headers(OWNER)).status_code in (200, 404, 400)
