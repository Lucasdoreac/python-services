import pytest
from mongomock import MongoClient

from configmodule import get_config


# Fixture to create an app with test context
@pytest.fixture
def app(monkeypatch):
    # Setting MonkeyPatch to replace MongoClient
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)

    # token_required é aplicado como decorator no MOMENTO em que cada
    # blueprint é importado -- o que só acontece dentro de create_app().
    # Por isso o monkeypatch em SLL.auth_decorators.token_required precisa
    # rodar ANTES de create_app(), senão as rotas já ficam presas à versão
    # original do decorator. Vira um passthrough: sem isso, todo teste que
    # bate numa rota autenticada toma 401 antes de chegar na lógica que o
    # teste realmente quer verificar (o auth de verdade -- e-mail + token
    # validados contra o auth_service -- é coberto pelo smoke.sh, que roda
    # com o auth_service de verdade de pé).
    monkeypatch.setattr('SLL.auth_decorators.token_required', lambda f: f)

    from SLL import create_app
    app = create_app(get_config())
    with app.app_context():
        yield app


# Fixture to create a Flask test client
@pytest.fixture
def client(app):
    return app.test_client()


class TestEndpoints:

    def test_register_reservation_succesfuly(self, monkeypatch, client):
        # Payload atualizado: FlowController.register_reservation_from_json
        # (index.py:45) e reservation_routes.post_reservation (:27) leem
        # data["eventId"], data["reservationDate"] e data["roomId"] -- o
        # payload antigo (room_id/course_id/date/start_time/end_time) não
        # batia com nenhuma dessas chaves.
        payload = {
            "eventId": "66193fb3e764a62988bbcf32",
            "reservationDate": "2031-04-25T10:00:00.000Z",
            "roomId": "661945b2e764a62988bbcf3e",
        }

        response = client.post('/reservations', json=payload)

        assert response.status_code == 201
        assert response.get_json() == {'success': "Reservation attempted"}

    def test_register_event_successfully(self, monkeypatch, client):
        # Payload atualizado: FlowController.event_data_build (index.py:294)
        # lê tituloEvento/classificacao/odsId/descricaoEvento (não
        # name/eventTypeId/odsTypeId/description) e exige userEmail -- que
        # post_event (events_routes.py:34) injeta a partir do header
        # "email", então não precisa vir no corpo.
        #
        # A asserção também estava desatualizada: o teste esperava 201 +
        # {'success': ...}, mas post_event (events_routes.py:43-54) sempre
        # devolve 200 (jsonify sem status explícito) + {'eventId': ...} --
        # e é exatamente isso que o frontend consome
        # (client.js:101: `return response.data.eventId`). Ajustado pra
        # verificar o contrato real, não o antigo.
        event = {
            "tituloEvento": "Palestra de Extensão",
            "classificacao": "lecture",
            "odsId": "odsId",
            "subscriptionLink": "subscriptionLink",
            "descricaoEvento": "description",
            "graduationId": "graduationId",
            "targetPublic": "targetPublic",
            "resources": "resources",
            "expectedSubscribers": "expectedSubscribers",
            "roomType": "roomType",
            "entrepreneuralPath": "entrepreneuralPath",
            "extensionProject": "extensionProject",
            "studentsMonitors": ["31891942", "30008021"],
            "eventLogo": "eventLogo",
        }

        response = client.post(
            '/events',
            json=event,
            headers={"email": "guilherme.amaral2004@gmail.com"},
        )

        assert response.status_code == 200
        body = response.get_json()
        assert "eventId" in body and body["eventId"]
