"""Especificações Swagger das rotas que não tinham documentação.

Complementa swagger_docs.get_swagger_specification (que devolvia None para
estas chaves). O teste Tests/swagger_coverage_tests.py exige que toda rota
apareça no /apidocs."""

_AUTH = [
    {"in": "header", "name": "email", "type": "string", "required": True, "description": "E-mail da pessoa logada"},
    {"in": "header", "name": "token", "type": "string", "required": True, "description": "Token do link de login"},
]
_LINK = [
    {"in": "query", "name": "eventId", "type": "string", "required": True, "description": "id do evento"},
    {"in": "query", "name": "tokenId", "type": "string", "required": True,
     "description": "Token de uso único enviado no e-mail de aprovação"},
]
_TOKEN_INVALIDO = {"description": "Token inexistente, já usado ou o evento já saiu desta etapa"}
_DRY_RUN = "Com EMAIL_DRY_RUN=true (padrão em dev) a rota devolve o HTML do e-mail em vez de enviá-lo."


def _spec(tag, summary, description, parameters, responses):
    return {"tags": [tag], "summary": summary, "description": description,
            "parameters": parameters, "responses": responses}


SPECS = {
    ("events", "PUT", None): _spec(
        "Events", "Atualizar um evento",
        "Grava o evento. Com status \"requested\" começa a aprovação (PDF + e-mail à Coordenação, ou aviso "
        "direto à Reitoria para aula/prova). O front usa POST /events/{event_id}/submit para enviar.",
        _AUTH + [{"in": "path", "name": "event_id", "type": "string", "required": True},
                 {"in": "body", "name": "evento", "required": True, "schema": {"type": "object"}}],
        {"200": {"description": "Evento gravado"}, "400": {"description": "Dados inválidos"},
         "404": {"description": "Evento não encontrado"}}),
    ("types", "GET", "collection"): _spec(
        "Types", "Tipos de uma coleção do catálogo",
        "Repassa ao catálogo GET /types/?collection_name={collection} (ex.: ODS, eventTypes).",
        _AUTH + [{"in": "path", "name": "collection", "type": "string", "required": True}],
        {"200": {"description": "Tipos da coleção"}, "404": {"description": "Coleção sem tipos"}}),
    ("campus", "GET", None): _spec(
        "Resources", "Listar campi", "Campi do catálogo (GraphQL).", _AUTH,
        {"200": {"description": "{\"campus\": [...]}"}, "404": {"description": "Nenhum campus"}}),
    ("rooms", "GET", "by-id"): _spec(
        "Resources", "Sala por id", "Sala do catálogo pelo id.",
        _AUTH + [{"in": "query", "name": "roomId", "type": "string", "required": True}],
        {"200": {"description": "Sala"}}),
    ("reservations", "GET", "by-event"): _spec(
        "Reservations", "Reservas de um evento", "Reservas gravadas para o evento.",
        _AUTH + [{"in": "query", "name": "eventId", "type": "string", "required": True}],
        {"200": {"description": "Lista de reservas"}, "400": {"description": "Faltou eventId"},
         "404": {"description": "Evento sem reservas"}}),
    ("auth", "PERMISSIONS", None): _spec(
        "Auth", "O que a pessoa logada pode ver no front",
        "Hoje só a tela de ofertas: manageOffers = e-mail está em OFFER_ADMIN_EMAILS.", _AUTH,
        {"200": {"description": "{\"manageOffers\": true|false}"}}),
    ("offers", "MANAGE", None): _spec(
        "Offers", "Ofertas para a tela de dias da semana",
        "20 ofertas por página, com disciplina, período, sala, professor, campus e dias (ISO: 1 = segunda). "
        "Só para quem está em OFFER_ADMIN_EMAILS.",
        _AUTH + [{"in": "query", "name": "year", "type": "integer", "description": "padrão: ano atual"},
                 {"in": "query", "name": "semester", "type": "integer", "description": "padrão: semestre atual"},
                 {"in": "query", "name": "discipline", "type": "string", "description": "parte do nome"},
                 {"in": "query", "name": "page", "type": "integer", "description": "padrão: 1"}],
        {"200": {"description": "{offers, page, pageSize, year, semester}"},
         "403": {"description": "Fora de OFFER_ADMIN_EMAILS"}, "502": {"description": "Catálogo indisponível"}}),
    ("offers", "WEEKDAYS", None): _spec(
        "Offers", "Definir os dias da semana de uma oferta",
        "Repassa ao PATCH /restapi/offers/{offer_id}/weekdays do catálogo. Sem dia, a aula não bloqueia sala. "
        "Só para quem está em OFFER_ADMIN_EMAILS; cada alteração vai para o log com o e-mail.",
        _AUTH + [{"in": "path", "name": "offer_id", "type": "string", "required": True},
                 {"in": "body", "name": "body", "required": True, "schema": {
                     "type": "object", "required": ["weekdays"],
                     "properties": {"weekdays": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 7}}}}}],
        {"200": {"description": "Oferta atualizada"}, "400": {"description": "weekdays inválido"},
         "403": {"description": "Fora de OFFER_ADMIN_EMAILS"}, "404": {"description": "Oferta não encontrada"},
         "502": {"description": "Catálogo indisponível"}}),
    ("approval", "ADMIN", None): _spec(
        "Approval", "Pré-visualizar o e-mail de aprovação",
        "Só em dry-run: devolve o e-mail da etapa (step 0 = Coordenação, 1 = Reitoria). " + _DRY_RUN,
        _LINK + [{"in": "query", "name": "step", "type": "integer", "required": True}],
        {"200": {"description": "HTML do e-mail"}, "404": _TOKEN_INVALIDO}),
    ("approval", "APPROVE", None): _spec(
        "Approval", "Aprovar o evento (link do e-mail)",
        "Coordenação aprova e o pedido segue para a Reitoria; Reitoria aprova e o evento fica aprovado. "
        "Avisa a pessoa solicitante. " + _DRY_RUN,
        _LINK + [{"in": "query", "name": "who", "type": "string", "required": True, "enum": ["coordenacao", "reitoria"]}],
        {"200": {"description": "Aprovado"}, "404": _TOKEN_INVALIDO}),
    ("approval", "REJECT", None): _spec(
        "Approval", "Recusar o evento (link do e-mail)", "Avisa a pessoa solicitante. " + _DRY_RUN,
        _LINK + [{"in": "query", "name": "who", "type": "string", "required": True, "enum": ["coordenacao", "reitoria"]}],
        {"200": {"description": "Recusado"}, "404": _TOKEN_INVALIDO}),
    ("approval", "CHANGES_GET", None): _spec(
        "Approval", "Formulário de pedido de mudança (link do e-mail da Coordenação)",
        "Abre o formulário onde a Coordenação escreve o que mudar. Não decide nada.", _LINK,
        {"200": {"description": "Formulário HTML"}, "403": {"description": "Token não é da Coordenação"},
         "404": _TOKEN_INVALIDO}),
    ("approval", "CHANGES_POST", None): _spec(
        "Approval", "Enviar o pedido de mudança",
        "Evento vai para requested_change, a mensagem fica em changesRequested e a pessoa solicitante recebe "
        "o pedido com o link de edição (FRONTEND_URL). " + _DRY_RUN,
        _LINK + [{"in": "formData", "name": "mudancas", "type": "string", "required": True}],
        {"200": {"description": "Pedido enviado"}, "400": {"description": "Mensagem vazia"},
         "403": {"description": "Token não é da Coordenação"}, "404": _TOKEN_INVALIDO}),
    ("approval", "NOTIFY", None): _spec(
        "Approval", "Avisar a Reitoria sobre uma reserva",
        "E-mail informativo à Reitoria (aula/prova aprovadas direto). " + _DRY_RUN,
        [{"in": "query", "name": "eventId", "type": "string", "required": True}],
        {"200": {"description": "Enviado (ou HTML em dry-run)"}, "400": {"description": "Faltou eventId"},
         "500": {"description": "Falha no envio"}}),
    ("/send-email", "POST", None): _spec(
        "Email", "Disparar e-mail transacional",
        "Dispara e-mail via Brevo ou simula em dry-run. Protegido por X-API-Key (CLOUD_FUNCTION_API_KEY).",
        [
            {"in": "header", "name": "X-API-Key", "type": "string", "required": True, "description": "Chave de autenticação da cloud function"},
            {"in": "body", "name": "email", "required": True, "schema": {
                "type": "object",
                "required": ["to", "subject", "content"],
                "properties": {
                    "to": {"type": "array", "items": {"type": "string"}, "description": "Destinatário(s)"},
                    "subject": {"type": "string", "description": "Assunto"},
                    "content": {"type": "string", "description": "Corpo do e-mail (HTML ou texto)"},
                    "is_html": {"type": "boolean", "default": True, "description": "Se o corpo é HTML"}
                }
            }}
        ],
        {"200": {"description": "E-mail enviado ou simulado"}, "400": {"description": "Parâmetros inválidos"},
         "401": {"description": "Chave de API inválida ou ausente"}, "502": {"description": "Erro no provedor de e-mail"}}),
    ("/events/<event_id>/pdf", "GET", None): _spec(
        "Events", "Download do PDF da reserva do evento",
        "Retorna o PDF gerado da reserva do evento armazenado diretamente no banco de dados.",
        [{"in": "path", "name": "event_id", "type": "string", "required": True, "description": "ID do evento"}],
        {"200": {"description": "Arquivo PDF da reserva"}, "404": {"description": "PDF não encontrado"}}),
}
