import pytest
from mongomock import MongoClient

from configmodule import get_config
from SLL import create_app


# Mesmo padrão de fixture de endpoints_tests.py: troca o MongoClient real por
# mongomock ANTES de create_app(), porque create_app() é quem chama
# MongoDBConnectionFactory.init_app(...) e, em seguida, importa (via
# blueprints) o módulo BLL.send_emails — que instancia SendEmailrepository()
# no import. Se importássemos BLL.send_emails no topo deste arquivo, isso
# rodaria na coleta do pytest, antes do monkeypatch, e quebraria com
# "MongoDBConnectionFactory has not been initialized".
@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr('pymongo.MongoClient', MongoClient)
    app = create_app(get_config())
    with app.app_context():
        yield app


COORDENACAO_BASE = ["base-coord@udf.edu.br"]
REITORIA_BASE = ["reitoria@udf.edu.br"]


def enable_real_sending(monkeypatch):
    """Liga o envio real (EMAIL_DRY_RUN=false) com destinatários de teste.

    Substitui o antigo `setenv("FLASK_ENV", "production")`: quem decide se
    e-mail sai agora é EMAIL_DRY_RUN, não o modo do Flask.
    """
    from settings import get_email_settings

    monkeypatch.setenv("EMAIL_DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_RECIPIENTS_COORDENACAO", ",".join(COORDENACAO_BASE))
    monkeypatch.setenv("EMAIL_RECIPIENTS_REITORIA", ",".join(REITORIA_BASE))
    monkeypatch.setenv("CLOUD_FUNCTION_URL", "https://fn.example")
    monkeypatch.setenv("CLOUD_FUNCTION_API_KEY", "chave")
    get_email_settings.cache_clear()
    return get_email_settings()


class TestSendToCoordenacaoRecipients:

    def test_does_not_leak_coordinator_between_calls(self, monkeypatch, app):
        """Regressão: emails["coordenacao"] é uma lista de módulo (send_emails.py:16-17)
        e send_to_coordenacao fazia .append() nela a cada chamada (send_emails.py:55),
        então o coordenador do evento 1 continuava na lista de destinatários do
        evento 2 (e de todo evento seguinte, para sempre).
        """
        from BLL import send_emails  # import tardio: ver comentário da fixture 'app'

        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"graduationId": f"grad-{event_id}"}),
        )
        monkeypatch.setattr(
            send_emails,
            "get_coordinator_by_graduation_id",
            lambda graduation_id: f"coord-{graduation_id}",
        )
        monkeypatch.setattr(
            send_emails,
            "find_teacher_email_by_id",
            lambda teacher_id: f"{teacher_id}@udf.edu.br",
        )

        captured_payloads = []

        class FakeResponse:
            status_code = 200

        def fake_post(url, json=None, headers=None):
            captured_payloads.append(json)
            return FakeResponse()

        monkeypatch.setattr(send_emails.requests, "post", fake_post)
        # Força o envio real: com EMAIL_DRY_RUN ligado (padrão) a função
        # devolve o HTML antes de montar/enviar o payload.
        enable_real_sending(monkeypatch)

        send_emails.send_to_coordenacao("event-1")
        send_emails.send_to_coordenacao("event-2")

        assert len(captured_payloads) == 2
        first_recipients = captured_payloads[0]["to"]
        second_recipients = captured_payloads[1]["to"]

        assert "coord-grad-event-1@udf.edu.br" in first_recipients
        assert "coord-grad-event-2@udf.edu.br" in second_recipients
        assert "coord-grad-event-1@udf.edu.br" not in second_recipients


class TestCoordinatorLookupGuards:
    """Regressão: get_coordinator_by_graduation_id e find_teacher_email_by_id
    estouravam IndexError/KeyError (send_emails.py:377,382 antes do fix) quando
    o curso não existia, não tinha coordenador, ou o coordenador não batia com
    nenhum professor cadastrado -- isso virava 500 pra quem chamasse
    send_to_coordenacao (administration_approval e events_routes.put_event).
    """

    def test_get_coordinator_returns_none_when_course_not_found(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_course_by_id",
            staticmethod(lambda graduation_id: []),
        )
        assert send_emails.get_coordinator_by_graduation_id("curso-inexistente") is None

    def test_get_coordinator_returns_none_when_field_missing(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_course_by_id",
            staticmethod(lambda graduation_id: [{"id": graduation_id, "name": "Curso sem coordenador"}]),
        )
        assert send_emails.get_coordinator_by_graduation_id("curso-sem-coordenador") is None

    def test_get_coordinator_returns_none_when_graduation_id_missing(self, monkeypatch, app):
        from BLL import send_emails

        assert send_emails.get_coordinator_by_graduation_id(None) is None
        assert send_emails.get_coordinator_by_graduation_id("") is None

    def test_find_teacher_email_returns_none_when_teacher_not_found(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_teachers_by_id",
            staticmethod(lambda teacher_id: []),
        )
        assert send_emails.find_teacher_email_by_id("professor-fantasma") is None

    def test_find_teacher_email_returns_none_when_id_missing(self, monkeypatch, app):
        from BLL import send_emails

        assert send_emails.find_teacher_email_by_id(None) is None
        assert send_emails.find_teacher_email_by_id("") is None


class TestSendToCoordenacaoWithoutCoordinator:
    """Fim a fim: evento cujo curso não tem coordenador identificável não pode
    mais derrubar o fluxo com 500 -- cai para a caixa padrão de Coordenação
    (emails["coordenacao"]) e o email sai normalmente.
    """

    def _patch_email_delivery(self, monkeypatch, send_emails):
        captured_payloads = []

        class FakeResponse:
            status_code = 200

        def fake_post(url, json=None, headers=None):
            captured_payloads.append(json)
            return FakeResponse()

        monkeypatch.setattr(send_emails.requests, "post", fake_post)
        enable_real_sending(monkeypatch)
        return captured_payloads

    def test_falls_back_to_default_mailbox_when_course_has_no_coordinator(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"graduationId": "curso-sem-coordenador"}),
        )
        monkeypatch.setattr(
            send_emails.GraphQlRequestMethods,
            "get_course_by_id",
            staticmethod(lambda graduation_id: [{"id": graduation_id, "coordinator": None}]),
        )
        captured_payloads = self._patch_email_delivery(monkeypatch, send_emails)

        # Não deve levantar exceção (antes: IndexError/KeyError -> 500).
        send_emails.send_to_coordenacao("event-sem-coordenador")

        assert len(captured_payloads) == 1
        assert captured_payloads[0]["to"] == ", ".join(COORDENACAO_BASE)

    def test_falls_back_when_event_has_no_graduation_id(self, monkeypatch, app):
        from BLL import send_emails

        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {}),  # evento sem graduationId
        )
        captured_payloads = self._patch_email_delivery(monkeypatch, send_emails)

        send_emails.send_to_coordenacao("event-sem-graduationId")

        assert len(captured_payloads) == 1
        assert captured_payloads[0]["to"] == ", ".join(COORDENACAO_BASE)


class TestApprovalTokenSingleUse:
    """Regressão issue #65: token do email de aprovação não é de uso único.

    Achado com dados reais do dev-local: cada visita a
    /administration_approval mintava um token novo pro mesmo (eventId,
    step) e abandonava o anterior, que ficava active para sempre e podia
    ser reaproveitado depois -- inclusive já com o evento decidido por
    outro token.
    """

    def test_verify_token_returns_false_for_unknown_token(self, monkeypatch, app):
        from BLL import send_emails

        # Antes: sem registro nenhum, a função "caía pro final" sem return
        # -> None. check_request só barrava `is False`, então um tokenId
        # forjado/inexistente passava pelo guard (`None is False` é False).
        assert send_emails.verify_token_from_email("token-que-nunca-existiu") is False

    def test_verify_token_true_while_event_still_pending_for_that_step(self, monkeypatch, app):
        from BLL import send_emails
        from utils.enums import EmailStep, EventStatus

        token = send_emails.create_send_email_token("event-1", EmailStep.COORDENACAO)
        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"status": EventStatus.WAITING.value}),
        )

        assert send_emails.verify_token_from_email(token) is True

    def test_verify_token_false_once_event_already_decided(self, monkeypatch, app):
        """O token continua 'active' no banco, mas o evento já saiu do
        status que essa etapa decide (decidido por outro caminho/token) --
        não pode mais valer."""
        from BLL import send_emails
        from utils.enums import EmailStep, EventStatus

        token = send_emails.create_send_email_token("event-1", EmailStep.COORDENACAO)
        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"status": EventStatus.APPROVED_BY_COORDENACAO.value}),
        )

        assert send_emails.verify_token_from_email(token) is False

    def test_creating_a_new_token_invalidates_the_previous_orphan_for_same_event_step(self, monkeypatch, app):
        """Reproduz o achado direto: /administration_approval remintando o
        token a cada visita não pode deixar o anterior 'active' pra
        sempre."""
        from BLL import send_emails
        from utils.enums import EmailStep, EventStatus

        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"status": EventStatus.WAITING.value}),
        )

        first_token = send_emails.create_send_email_token("event-1", EmailStep.COORDENACAO)
        assert send_emails.verify_token_from_email(first_token) is True

        second_token = send_emails.create_send_email_token("event-1", EmailStep.COORDENACAO)

        assert first_token != second_token
        assert send_emails.verify_token_from_email(first_token) is False
        assert send_emails.verify_token_from_email(second_token) is True

    def test_creating_a_new_token_does_not_touch_other_events_or_steps(self, monkeypatch, app):
        from BLL import send_emails
        from utils.enums import EmailStep, EventStatus

        # Um único mock, indexado por event_id, pra cada evento manter seu
        # próprio status coerente independente da ordem das chamadas abaixo
        # (senão sobrescrever o mock a cada create_send_email_token faria a
        # verificação final usar sempre o último status, não o de cada
        # evento no momento em que seu token foi criado).
        statuses = {
            "event-other": EventStatus.WAITING.value,
            "event-1": EventStatus.APPROVED_BY_COORDENACAO.value,
        }
        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"status": statuses[event_id]}),
        )

        other_event_token = send_emails.create_send_email_token("event-other", EmailStep.COORDENACAO)
        other_step_token = send_emails.create_send_email_token("event-1", EmailStep.REITORIA)

        # Emitir um novo token de COORDENACAO pro event-1 não pode desativar
        # o token de outro evento, nem o de outra etapa do mesmo evento.
        send_emails.create_send_email_token("event-1", EmailStep.COORDENACAO)

        assert send_emails.verify_token_from_email(other_event_token) is True
        assert send_emails.verify_token_from_email(other_step_token) is True


class TestEmailDryRun:
    """EMAIL_DRY_RUN é o único interruptor de envio (antes: um
    `FLASK_ENV == "development"` repetido em cada função de envio)."""

    def _forbid_post(self, monkeypatch, send_emails):
        def fail(*args, **kwargs):
            raise AssertionError("requests.post não deveria ser chamado em dry-run")

        monkeypatch.setattr(send_emails.requests, "post", fail)

    def _stub_event_lookups(self, monkeypatch, send_emails):
        monkeypatch.setattr(
            send_emails.FlowController,
            "find_event_by_event_id",
            staticmethod(lambda event_id: {"graduationId": "curso"}),
        )
        monkeypatch.setattr(send_emails, "get_coordinator_by_graduation_id", lambda g: None)

    def test_coordenacao_default_does_not_send_and_returns_html(self, monkeypatch, app):
        from BLL import send_emails
        from settings import get_email_settings

        # Mesmo com FLASK_ENV=production: o interruptor é EMAIL_DRY_RUN.
        monkeypatch.setenv("FLASK_ENV", "production")
        monkeypatch.delenv("EMAIL_DRY_RUN", raising=False)
        get_email_settings.cache_clear()
        self._forbid_post(monkeypatch, send_emails)
        self._stub_event_lookups(monkeypatch, send_emails)

        result = send_emails.send_to_coordenacao("event-1")

        assert isinstance(result, str) and "<html" in result.lower()

    def test_reitoria_default_does_not_send_and_returns_html(self, monkeypatch, app):
        from BLL import send_emails
        from settings import get_email_settings

        monkeypatch.setenv("FLASK_ENV", "production")
        monkeypatch.delenv("EMAIL_DRY_RUN", raising=False)
        get_email_settings.cache_clear()
        self._forbid_post(monkeypatch, send_emails)

        result = send_emails.send_to_reitoria("event-1")

        assert isinstance(result, str) and "<html" in result.lower()

    def test_reitoria_real_sending_uses_configured_recipients(self, monkeypatch, app):
        from BLL import send_emails

        captured = []

        class FakeResponse:
            status_code = 200

        monkeypatch.setattr(
            send_emails.requests,
            "post",
            lambda url, json=None, headers=None: captured.append((url, json, headers)) or FakeResponse(),
        )
        enable_real_sending(monkeypatch)

        send_emails.send_to_reitoria("event-1")

        (url, payload, headers), = captured
        assert url == "https://fn.example/send-email"
        assert payload["to"] == ", ".join(REITORIA_BASE)
        assert headers["X-API-Key"] == "chave"

    def test_no_hardcoded_personal_recipients_left_in_code(self):
        """PRIV-01: endereços pessoais de devs ficavam fixos em send_emails.py."""
        import pathlib

        source = pathlib.Path(__file__).resolve().parents[1] / "BLL" / "send_emails.py"
        text = source.read_text()

        for personal in ("danrleywillian@gmail.com", "guilherme.amaral2004@gmail.com",
                         "dwcorpbrasil@gmail.com", "danrley.pereira@cs.udf.edu.br",
                         "udf.edu.br"):
            assert personal not in text
