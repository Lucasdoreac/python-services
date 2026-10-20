"""Geração do PDF (Typst): texto do usuário nunca vira marcação, e cada geração usa seu diretório."""

import os

import pytest

EVENT = {
    "name": "Palestra",
    "organizer": {"email": "dono@udf.edu.br", "phone": "61 99999-0000", "name": "dono"},
    "eventTypeId": "lecture",
    "odsId": "1",
    "description": "d",
    "graduationId": "curso",
    "targetPublic": "alunos",
    "resources": "projetor",
    "expectedSubscribers": "30",
    "roomType": "auditório",
    "entrepreneuralPath": "",
    "extensionProject": "",
    "studentsMonitors": "",
}


@pytest.fixture
def pdf(client):
    from BLL import pdf as module

    return module


@pytest.fixture
def generated(pdf, monkeypatch):
    """Executa generate_event_pdf e devolve (bytes do PDF, diretório usado)."""
    captured = {}

    def fake_save(event_id, local_pdf_path):
        captured["dir"] = os.path.dirname(local_pdf_path)
        with open(local_pdf_path, "rb") as pdf_file:
            captured["bytes"] = pdf_file.read()

    monkeypatch.setattr(pdf, "save_pdf", fake_save)
    monkeypatch.setattr(pdf.FlowController, "find_types_by_collection", lambda collection: {"types": []})
    monkeypatch.setattr(pdf.FlowController, "find_reservation_by_event_id", lambda event_id: [])

    def run(**overrides):
        event = {**EVENT, **overrides}
        monkeypatch.setattr(pdf.FlowController, "find_event_by_event_id", lambda event_id: event)
        pdf.generate_event_pdf(event_id="e1")
        return captured["bytes"], captured["dir"]

    return run


def test_a_normal_event_produces_a_pdf(generated):
    content, _ = generated()
    assert content.startswith(b"%PDF")


@pytest.mark.parametrize("hostile", [
    '`] #panic("injected") [`',
    '#panic("injected")',
    "]\n#let x = 1 / 0\n[",
    "```\n#read(\"/etc/passwd\")\n```",
])
def test_markup_in_a_field_is_rendered_as_text_not_executed(generated, hostile):
    content, _ = generated(description=hostile, roomType=hostile)
    assert content.startswith(b"%PDF")


def test_each_generation_uses_its_own_temporary_directory(generated):
    _, first = generated()
    _, second = generated()
    assert first != second
    assert not os.path.exists(first)  # removed when the generation ends
    assert not os.path.exists(os.path.join("PDFs", "evento.pdf.test-marker"))


def test_fields_are_text_and_length_capped(pdf):
    fields = pdf.pdf_fields({"description": "x" * 5000, "room": None, "n": 7})
    assert len(fields["description"]) == pdf.PDF_FIELD_LIMIT
    assert fields["room"] == "" and fields["n"] == "7"
