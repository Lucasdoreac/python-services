FROM python:3.14.8-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get upgrade --yes --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.4.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=10000

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi

COPY . .

EXPOSE 10000
CMD ["sh", "-c", "exec gunicorn --workers 2 --bind 0.0.0.0:${PORT:-10000} main:reservation_app"]
