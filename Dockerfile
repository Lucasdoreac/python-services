# Não existia Dockerfile nenhum pra esse serviço em lugar nenhum (nem na
# main, nem em nenhum PR aberto) -- dev-local rodava via `python:3.12-slim`
# + pip install ad-hoc a cada `up`, sem lockfile, sem imagem de verdade.
# Escrito seguindo o mesmo padrão do PR #25 (shared-resources): Poetry +
# Gunicorn, imagem construída.
FROM python:3.13.3-slim

WORKDIR /python-services

COPY . .

RUN pip install poetry

ENV PATH="/root/.local/bin:$PATH"

RUN poetry config virtualenvs.create false

# `poetry lock` antes do install: pyproject.toml ganhou sib-api-v3-sdk (já
# usado no código, nunca declarado) e o poetry.lock existente não reflete
# isso. Regenerar no build evita "pyproject.toml changed significantly
# since poetry.lock was last generated".
RUN poetry lock
RUN poetry install --no-root

EXPOSE 5000

CMD ["sh", "-c", "PYTHONPATH=src poetry run gunicorn -w 2 -b 0.0.0.0:5000 main:reservation_app"]
