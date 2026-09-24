# Configuração da API do Reservas (python-services)

Todas as variáveis que o código lê, e só elas, estão em [`.env.example`](../.env.example).
O teste `src/Tests/env_example_tests.py` falha se uma variável nova não for documentada
ou se o exemplo listar algo que o código não usa.

Coluna **Prod**: ✅ obrigatória em produção · ⚠️ tem padrão, mas o padrão não serve em
produção · — opcional.

## Variáveis

| Variável | Prod | Exemplo | Para que serve | Se faltar |
|---|---|---|---|---|
| `FLASK_ENV` | — | `production` | `development` liga a config de dev do Flask. Não controla e-mail. | Vale `production`. |
| `MONGO_URI` | ✅ ou o trio abaixo | `mongodb+srv://u:s@host/` | Conexão completa com o MongoDB. | Monta `mongodb+srv://` com o trio abaixo. |
| `MONGO_HOST` / `MONGO_USERNAME` / `MONGO_PASSWORD` | ✅ se não houver `MONGO_URI` | Atlas | Alternativa ao `MONGO_URI` (Atlas, `mongodb+srv`). | Sem nenhum dos dois, a API não conecta. |
| `MONGO_DATABASE` | ✅ | `rooms-reservation-app` | Banco das reservas e eventos. | Falha ao acessar o banco. |
| `URL_AUTH` | ✅ | `https://auth.exemplo` | auth_service: valida o login e envia o link de acesso. | Todo login e toda rota autenticada falham. |
| `URL_graph` | ✅ | `https://catalogo.exemplo/graphql/` | Catálogo (GraphQL): tipos, cursos e ofertas (bloqueio de sala). | Busca de salas livres responde 500. |
| `URL_restapi` | ✅ | `https://catalogo.exemplo/restapi` | Catálogo (REST): salas, campus e cursos. | Listas vazias ou erro. |
| `INTERNAL_API_KEY` | ✅ | — | Chave enviada no header `x-api-key` a toda chamada ao catálogo (REST e GraphQL). Tem de estar no `API_KEY_LIST` do internal_apis. | O catálogo responde 403: busca de salas, cursos e tipos falham. |
| `SERVER_NAME` | ⚠️ | `reservas-api.exemplo` | Host público da API, usado nos links de aprovar/rejeitar dos e-mails. | Os links saem para `localhost:5000` e não abrem fora do servidor. |
| `SERVER_SCHEME` | ⚠️ | `https` | Esquema dos links de aprovar/rejeitar nos e-mails (`PREFERRED_URL_SCHEME` do Flask). Atrás de HTTPS: `https`. | Vale `http`: links `http://`. |
| `MINIO_URL` | ✅ | `https://arquivos.exemplo:9000` | Endereço **público, com esquema**, do MinIO: links do PDF e ícones nos e-mails, caminho gravado do PDF. | Links quebrados (`None/labtech/...`). |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | ✅ | — | Credenciais para subir o PDF do evento. | O PDF não sobe (erro só no stdout, via `print`). |
| `EMAIL_DRY_RUN` | ⚠️ | `false` | `true` (padrão) não envia nada: as rotas devolvem o HTML. Produção: `false`. | Nenhum e-mail sai. |
| `EMAIL_RECIPIENTS_COORDENACAO` | ✅ se envio ligado | `a@udf.edu.br,b@udf.edu.br` | Caixa padrão da Coordenação quando o curso não tem coordenador. | Com `EMAIL_DRY_RUN=false`, a API não sobe (erro na partida). |
| `EMAIL_RECIPIENTS_REITORIA` | ✅ se envio ligado | `reitoria@udf.edu.br` | Destinatários da Reitoria. | Idem. |
| `CLOUD_FUNCTION_URL` / `CLOUD_FUNCTION_API_KEY` | ✅ se envio ligado | — | Função que entrega os e-mails. | Idem. |
| `AUTH_ALLOWED_DOMAIN` | — | `udf.edu.br` | Domínio que pode pedir link de login. | Vale `udf.edu.br`. |
| `AUTH_ALLOWED_EMAILS` | — | `parceiro@ex.com` | Exceções individuais ao domínio, separadas por vírgula. | Só o domínio entra. |
| `OFFER_PERIOD_HOURS` | ⚠️ | `manhã=07:30-11:50,noite=19:00-22:40` | Horário que cada período de aula ocupa a sala (issue #29). Nome do período sem diferença de maiúsculas. | Vale o padrão provisório `manhã=07:00-12:00,tarde=13:00-18:00,noite=19:00-23:00`; confirmar com a Coordenação. |

A API **falha na partida** (de propósito) se `EMAIL_DRY_RUN=false` sem destinatários, URL
ou chave da Cloud Function: é melhor não subir do que aprovar evento sem avisar ninguém.

## Checklist de produção
1. Mongo: `MONGO_URI` (ou o trio) + `MONGO_DATABASE`.
2. Serviços: `URL_AUTH`, `URL_graph`, `URL_restapi` apontando para o auth_service e o internal_apis de produção, e `INTERNAL_API_KEY` = uma chave do `API_KEY_LIST` do internal_apis.
3. Links: `SERVER_NAME` = host público da API e `SERVER_SCHEME=https`; `MINIO_URL` = endereço público do MinIO com `https://`.
4. E-mail: `EMAIL_DRY_RUN=false` + destinatários + Cloud Function.
5. Login: conferir `AUTH_ALLOWED_DOMAIN` e, se houver, `AUTH_ALLOWED_EMAILS`.
6. Aulas: `OFFER_PERIOD_HOURS` com os horários reais dos períodos.
7. Depois de subir: `py_log.log` antigo (versões anteriores gravavam tokens em claro) deve ser apagado ou rotacionado.

## Problemas conhecidos
- **`src/SLL/sendblue.py` é código morto** (nenhum módulo o importa); por isso
  `APIKEYSECRET`, `SMTP*`, `EMAIL` e `REACT` não entram no `.env.example`.
