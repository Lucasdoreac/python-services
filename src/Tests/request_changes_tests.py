"""Coordenação pede mudança no evento (issue #35; retoma o PR #63).

Antes, o link "Solicitar alterações" do e-mail só desativava o token: o
evento continuava "waiting", a pessoa solicitante não recebia nada e não
havia onde escrever o que mudar.

Agora o link abre um formulário; ao enviar, o evento vai para
requested_change, a mensagem fica gravada no evento e a pessoa solicitante
recebe um e-mail com a mensagem e o link para editar o evento no front."""
import pytest
from bson import ObjectId
from mongomock import MongoClient

from configmodule import get_config
from DAL import MongoDBConnectionFactory

FRONT = "https://reservas.example"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    monkeypatch.setenv("FRONTEND_URL", FRONT)
    from settings import get_email_settings
    get_email_settings.cache_clear()
    from SLL import create_app
    app = create_app(get_config())
    with app.app_context():
        yield app.test_client()
    get_email_settings.cache_clear()


def db():
    return MongoDBConnectionFactory.get_db()


def waiting_event(status="waiting"):
    return str(db().events.insert_one({
        "tituloEvento": "Palestra", "classificacao": "lecture", "status": status,
        "organizer": {"email": "prof@udf.edu.br"}}).inserted_id)


def token(event_id, step):
    from BLL.send_emails import create_send_email_token
    from utils.enums import EmailStep
    return create_send_email_token(event_id, EmailStep(step))


def event(event_id):
    return db().events.find_one({"_id": ObjectId(event_id)})


def url(event_id, tok):
    return f"/request_changes?eventId={event_id}&tokenId={tok}"


def test_link_opens_form_that_posts_back_with_the_token(client):
    event_id = waiting_event()
    tok = token(event_id, 0)
    res = client.get(url(event_id, tok))
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'name="mudancas"' in html
    assert 'method="post"' in html and tok in html
    assert event(event_id)["status"] == "waiting"  # abrir o formulário não decide nada


def test_sending_changes_updates_event_and_emails_the_requester(client):
    event_id = waiting_event()
    tok = token(event_id, 0)
    res = client.post(url(event_id, tok), data={"mudancas": "Trocar a sala para o auditório."})
    assert res.status_code == 200
    doc = event(event_id)
    assert doc["status"] == "requested_change"
    assert doc["changesRequested"] == "Trocar a sala para o auditório."
    email = res.get_data(as_text=True)  # EMAIL_DRY_RUN: a rota devolve o e-mail
    assert "Trocar a sala para o auditório." in email
    assert f"{FRONT}/event/type-selection?eventId={event_id}" in email
    # uso único: o mesmo link não decide duas vezes
    assert client.post(url(event_id, tok), data={"mudancas": "outra"}).status_code == 404


def test_empty_message_is_400_and_nothing_changes(client):
    event_id = waiting_event()
    tok = token(event_id, 0)
    assert client.post(url(event_id, tok), data={"mudancas": "   "}).status_code == 400
    assert event(event_id)["status"] == "waiting"
    assert client.get(url(event_id, tok)).status_code == 200  # token continua valendo


def test_only_coordination_token_can_request_changes(client):
    event_id = waiting_event(status="approved_by_coordenacao")
    tok = token(event_id, 1)  # token da Reitoria
    assert client.post(url(event_id, tok), data={"mudancas": "x"}).status_code == 403
    assert event(event_id)["status"] == "approved_by_coordenacao"


def test_message_is_escaped_in_the_email(client):
    event_id = waiting_event()
    res = client.post(url(event_id, token(event_id, 0)), data={"mudancas": "<script>x</script>"})
    assert "<script>" not in res.get_data(as_text=True)
