import mongomock
import pytest


class FakeMinio:
    uploads = []
    files = []

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint

    def bucket_exists(self, bucket):
        return True

    def fput_object(self, bucket, object_name, path, content_type=None):
        FakeMinio.uploads.append((self.endpoint, bucket, object_name))
        with open(path, "rb") as f:
            FakeMinio.files.append((path, f.read(4)))


class FakeReservationManager:
    saved = []

    def insert_pdf(self, data):
        FakeReservationManager.saved.append(data)


@pytest.fixture
def pdf(monkeypatch):
    # BLL cria repositórios na importação e eles pedem o Mongo.
    from DAL import MongoDBConnectionFactory
    monkeypatch.setattr(MongoDBConnectionFactory, "_client", mongomock.MongoClient())
    monkeypatch.setattr(MongoDBConnectionFactory, "_database", "test-pdf")
    from BLL import pdf
    return pdf


@pytest.fixture(autouse=True)
def fakes(monkeypatch, pdf):
    FakeMinio.uploads, FakeMinio.files, FakeReservationManager.saved = [], [], []
    monkeypatch.setattr(pdf, "Minio", FakeMinio)
    monkeypatch.setattr(pdf, "ReservationManager", FakeReservationManager)
    monkeypatch.setenv("MINIO_ACCESS_KEY", "k")
    monkeypatch.setenv("MINIO_SECRET_KEY", "s")


def test_pdf_path_uses_the_configured_minio_url(monkeypatch, pdf):
    # O caminho gravado era fixo em dwcorp.com.br:9000 (host de produção sem
    # esquema), então nenhum outro ambiente achava o PDF. Agora segue
    # MINIO_URL, igual ao link do PDF nos e-mails (send_emails.py).
    monkeypatch.setenv("MINIO_URL", "http://minio.exemplo:9000")

    pdf.save_pdf("ev1", "PDFs/evento.pdf")

    assert FakeMinio.uploads == [("minio.exemplo:9000", "labtech", "reservation-pdfs/ev1.pdf")]
    assert FakeReservationManager.saved == [
        {"path": "http://minio.exemplo:9000/labtech/reservation-pdfs/ev1.pdf", "eventId": "ev1"}
    ]


def test_trailing_slash_in_minio_url_does_not_double(monkeypatch, pdf):
    monkeypatch.setenv("MINIO_URL", "https://arquivos.udf.edu.br/")

    pdf.save_pdf("ev2", "PDFs/evento.pdf")

    assert FakeReservationManager.saved[0]["path"] == "https://arquivos.udf.edu.br/labtech/reservation-pdfs/ev2.pdf"


def event(name):
    return {
        "name": name, "organizer": {"name": "Prof", "email": "p@udf.edu.br", "phone": "61"},
        "eventTypeId": "lecture", "odsId": "3", "subscriptionLink": "", "description": "d",
        "graduationId": 31, "targetPublic": [], "resources": [], "expectedSubscribers": 10,
        "roomType": "101", "entrepreneuralPath": "", "extensionProject": "", "studentsMonitors": [],
        "eventLogo": "", "status": "waiting",
    }


def test_generating_pdf_does_not_touch_tracked_files_nor_share_a_path(monkeypatch, pdf):
    # Antes todo evento escrevia em PDFs/evento.pdf (versionado): rodar o fluxo
    # sujava o git e duas aprovações simultâneas podiam subir o PDF de um
    # evento com o nome do outro (DEV-01).
    import hashlib, pathlib
    monkeypatch.setenv("MINIO_URL", "http://minio:9000")
    events = {"ev-a": event("Evento A"), "ev-b": event("Evento B")}
    monkeypatch.setattr(pdf.FlowController, "find_types_by_collection", lambda c: {"types": [{"id": "3", "name": "Saúde"}]})
    monkeypatch.setattr(pdf.FlowController, "find_event_by_event_id", lambda i: events[i])
    monkeypatch.setattr(pdf.FlowController, "find_reservation_by_event_id", lambda i: [])
    tracked = {f: hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
               for f in ("PDFs/evento.pdf", "PDFs/evento.typ")}

    pdf.generate_event_pdf("ev-a")
    pdf.generate_event_pdf("ev-b")

    paths = [path for path, _ in FakeMinio.files]
    assert all(head == b"%PDF" for _, head in FakeMinio.files)
    assert len(set(paths)) == 2
    assert not any(pathlib.Path(p).resolve().is_relative_to(pathlib.Path("PDFs").resolve()) for p in paths)
    assert not any(pathlib.Path(p).exists() for p in paths)  # temporário apagado
    assert tracked == {f: hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() for f in tracked}
