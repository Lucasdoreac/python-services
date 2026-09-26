"""Testes de armazenamento de PDF sem MinIO e da rota pública GET /events/<id>/pdf.

Substitui o MinIO como dependência obrigatória: o PDF é guardado no MongoDB
e servido diretamente pela API, funcionando tanto em desenvolvimento quanto no Render.
"""
import pytest
from mongomock import MongoClient

from configmodule import get_config
from SLL import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    app = create_app(get_config())
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def a_pdf(tmp_path):
    p = tmp_path / "teste.pdf"
    p.write_bytes(b"%PDF-1.7 conteudo de teste")
    return str(p)


def test_save_pdf_without_minio_stores_content_in_mongo(app, tmp_path, monkeypatch):
    from BLL import pdf
    from DAL import ReservationManager

    monkeypatch.setenv("MINIO_URL", "")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "")
    monkeypatch.setenv("MINIO_SECRET_KEY", "")

    pdf_file = a_pdf(tmp_path)
    pdf.save_pdf("ev-mongo-1", pdf_file)

    rm = ReservationManager()
    saved = rm.get_pdf_by_event_id("ev-mongo-1")
    assert saved is not None
    assert saved.get("eventId") == "ev-mongo-1"
    assert saved.get("content") == b"%PDF-1.7 conteudo de teste"


def test_get_event_pdf_route_returns_pdf(client, tmp_path, monkeypatch):
    from BLL import pdf
    monkeypatch.setenv("MINIO_URL", "")

    pdf.save_pdf("ev-rota-1", a_pdf(tmp_path))

    res = client.get("/events/ev-rota-1/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("Content-Type", "")
    assert res.data == b"%PDF-1.7 conteudo de teste"


def test_get_event_pdf_route_not_found(client):
    res = client.get("/events/ev-inexistente/pdf")
    assert res.status_code == 404
