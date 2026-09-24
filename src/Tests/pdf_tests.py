import mongomock
import pytest


class FakeMinio:
    uploads = []

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint

    def bucket_exists(self, bucket):
        return True

    def fput_object(self, bucket, object_name, path, content_type=None):
        FakeMinio.uploads.append((self.endpoint, bucket, object_name))


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
    FakeMinio.uploads, FakeReservationManager.saved = [], []
    monkeypatch.setattr(pdf, "Minio", FakeMinio)
    monkeypatch.setattr(pdf, "ReservationManager", FakeReservationManager)
    monkeypatch.setenv("MINIO_ACCESS_KEY", "k")
    monkeypatch.setenv("MINIO_SECRET_KEY", "s")


def test_pdf_path_uses_the_configured_minio_url(monkeypatch, pdf):
    # O caminho gravado era fixo em dwcorp.com.br:9000 (host de produção sem
    # esquema), então nenhum outro ambiente achava o PDF. Agora segue
    # MINIO_URL, igual ao link do PDF nos e-mails (send_emails.py).
    monkeypatch.setenv("MINIO_URL", "http://minio.exemplo:9000")

    pdf.save_pdf("ev1")

    assert FakeMinio.uploads == [("minio.exemplo:9000", "labtech", "reservation-pdfs/ev1.pdf")]
    assert FakeReservationManager.saved == [
        {"path": "http://minio.exemplo:9000/labtech/reservation-pdfs/ev1.pdf", "eventId": "ev1"}
    ]


def test_trailing_slash_in_minio_url_does_not_double(monkeypatch, pdf):
    monkeypatch.setenv("MINIO_URL", "https://arquivos.udf.edu.br/")

    pdf.save_pdf("ev2")

    assert FakeReservationManager.saved[0]["path"] == "https://arquivos.udf.edu.br/labtech/reservation-pdfs/ev2.pdf"
