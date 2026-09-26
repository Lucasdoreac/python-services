# Não existia Dockerfile nenhum pra esse serviço em lugar nenhum (nem na
# main, nem em nenhum PR aberto) -- dev-local rodava via `python:3.12-slim`
# + pip install ad-hoc a cada `up`, sem lockfile, sem imagem de verdade.
# Escrito seguindo o mesmo padrão do PR #25 (shared-resources): Poetry +
# Gunicorn, imagem construída.
FROM python:3.13.15-slim

WORKDIR /python-services

COPY . .

RUN pip install poetry

ENV PATH="/root/.local/bin:$PATH"

RUN poetry config virtualenvs.create false

# O poetry.lock versionado é a fonte da verdade (`poetry check --lock` passa);
# o build não re-resolve dependências.
RUN poetry install --no-root

EXPOSE 5000

CMD ["sh", "-c", "PYTHONPATH=src poetry run gunicorn -w 2 -b 0.0.0.0:${PORT:-5000} main:reservation_app"]
