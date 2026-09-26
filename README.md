# python-services

Guia de como baixar os serviços necessários para a execução do projeto Back-And.

## Ferramentas - Configurando ambiente

[![Pycharm](https://img.shields.io/badge/PYCHARM-000000)](https://www.jetbrains.com/help/pycharm/getting-started.html)
[![Poetry](https://img.shields.io/badge/POETRY-000000)](https://python-poetry.org/docs/)
[![Dotenv](https://img.shields.io/badge/DOTENV-000000)](https://www.dotenv.org/docs/)

## Poetry
O Poetry é uma ferramenta para gerenciamento de dependências e empacotamento em Python. Ele facilita a instalação de bibliotecas, criação de ambientes virtuais e publicação de projetos.

[Install Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)

## PyCharm
PyCharm é um ambiente de desenvolvimento integrado (IDE) para Python, desenvolvido pela JetBrains.

> [!IMPORTANT]
> Não instale em "C:\Program Files\JetBrains\PyCharm 2024", use um caminho sem espaços (e.g. "C:\jetbrains\pycharm2024\"). Isso é importante para evitar problemas com o Poetry e com a depuração (modo debugger no PyCharm).

[Install Pycharm](https://www.jetbrains.com/pycharm/download/)

## Criando ambiente virtual

1. poetry env use python3.12

### Se quiser ativar o ambiente virtual

```bash
poetry shell
```

## Instalar e configurar o Poetry no PyCharm
https://www.jetbrains.com/help/pycharm/poetry.html#poetry-env


## Instalar dependências com Poetry
```bash
poetry install
```

## Deploy no Render (Blueprint render.yaml)

O repositório possui o arquivo [`render.yaml`](./render.yaml) configurado para implantar toda a infraestrutura da aplicação (4 serviços web interligados) usando a hospedagem gratuita (Free Tier) do Render.

### Serviços criados pelo Blueprint:
1. **`reservas-web`**: Frontend SPA (React / Vite) compilado como site estático.
2. **`reservas-catalog`**: Catálogo Acadêmico (`internal_apis`), executado via Docker.
3. **`reservas-auth`**: Serviço de Autenticação / Magic Link (`auth_service`), executado via Docker.
4. **`reservas-api`**: API Principal de Reservas e E-mails (`python-services`), executado via Docker.

### Passo a Passo para Implantação:
1. **Acesse o Dashboard do Render**:
   - Faça login na conta do Render ([render.com](https://render.com)).
2. **Criar Blueprint**:
   - Clique em **New +** e selecione **Blueprint**.
   - Conecte o repositório GitHub contendo o arquivo `render.yaml`.
3. **Configurar Variáveis de Ambiente pendentes (`sync: false`)**:
   Durante a criação do Blueprint, o Render solicitará o preenchimento das variáveis marcadas com `sync: false`:
   - `MONGO_URI`: String de conexão com o MongoDB (ex.: MongoDB Atlas `mongodb+srv://...`).
   - `BREVO_API_KEY`: Chave de API do Brevo para envio de e-mails.
   - `BREVO_SENDER_EMAIL`: E-mail remetente cadastrado no Brevo.
   - `EMAIL_RECIPIENTS_COORDENACAO`: E-mails da coordenação (separados por vírgula).
   - `EMAIL_RECIPIENTS_REITORIA`: E-mails da reitoria (separados por vírgula).
   - `REDIS_URL` (opcional / se utilizado nos microserviços).
   - `OFFER_ADMIN_EMAILS` (opcional).
4. **Finalizar a Implantação**:
   - Clique em **Apply**. O Render iniciará a criação e orquestração automática de todos os 4 serviços interligados.
