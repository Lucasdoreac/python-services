FROM python:3.14.7-slim AS builder

ENV POETRY_VERSION=2.4.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi \
    && rm -rf /app/.venv/lib/python3.14/site-packages/pip* /app/.venv/bin/pip*

FROM python:3.14.7-slim AS runtime

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall --yes pip

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=10000

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY . .

EXPOSE 10000
CMD ["sh", "-c", "exec gunicorn --workers 2 --bind 0.0.0.0:${PORT:-10000} main:reservation_app"]
