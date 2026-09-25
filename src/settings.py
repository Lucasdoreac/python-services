"""Configuração de e-mail: tipada, validada e lida de variáveis de ambiente.

Antes, o "não envia e-mail em dev" dependia de `os.getenv("FLASK_ENV") ==
"development"` repetido em vários pontos, e os destinatários (inclusive
endereços pessoais) ficavam fixos em send_emails.py. Aqui há um único
interruptor explícito (EMAIL_DRY_RUN) e os destinatários vêm do ambiente.
FLASK_ENV continua existindo, mas só escolhe a configuração do Flask
(configmodule.py); não decide mais se e-mail sai.

Variáveis:
    EMAIL_DRY_RUN                  true (padrão) = nada é enviado; false = envia de verdade
    EMAIL_RECIPIENTS_COORDENACAO   e-mails separados por vírgula
    EMAIL_RECIPIENTS_REITORIA      e-mails separados por vírgula
    CLOUD_FUNCTION_URL             obrigatória quando EMAIL_DRY_RUN=false
    CLOUD_FUNCTION_API_KEY         obrigatória quando EMAIL_DRY_RUN=false
    FRONTEND_URL                   endereço público do front (links nos e-mails)
    AUTH_ALLOWED_DOMAIN            domínio que pode pedir link de login (padrão udf.edu.br)
    AUTH_ALLOWED_EMAILS            exceções individuais, separadas por vírgula
    OFFER_PERIOD_HOURS             horário de cada período de aula, "manhã=07:00-12:00,..."
"""
from datetime import time
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class EmailSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    email_dry_run: bool = True
    email_recipients_coordenacao: Annotated[list[str], NoDecode] = []
    email_recipients_reitoria: Annotated[list[str], NoDecode] = []
    cloud_function_url: str | None = None
    cloud_function_api_key: str | None = None
    # front do Reservas: link "editar o evento" no e-mail de pedido de mudança
    frontend_url: str = "http://localhost:3000"

    @field_validator("email_recipients_coordenacao", "email_recipients_reitoria", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cloud_function_url", "cloud_function_api_key", mode="before")
    @classmethod
    def _empty_is_none(cls, value):
        # `CLOUD_FUNCTION_URL=` (vazio) no .env deve valer "não definida".
        return value or None

    @model_validator(mode="after")
    def _require_config_when_sending(self):
        if self.email_dry_run:
            return self
        missing = [
            name
            for name, value in (
                ("EMAIL_RECIPIENTS_COORDENACAO", self.email_recipients_coordenacao),
                ("EMAIL_RECIPIENTS_REITORIA", self.email_recipients_reitoria),
                ("CLOUD_FUNCTION_URL", self.cloud_function_url),
                ("CLOUD_FUNCTION_API_KEY", self.cloud_function_api_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "EMAIL_DRY_RUN=false exige configuração de envio, faltando: " + ", ".join(missing)
            )
        return self


@lru_cache
def get_email_settings() -> EmailSettings:
    return EmailSettings()


class AuthSettings(BaseSettings):
    """Quem pode pedir link de login. Antes: domínio e uma exceção pessoal
    fixos em SLL/auth_routes.py."""

    model_config = SettingsConfigDict(extra="ignore")

    auth_allowed_domain: str = "udf.edu.br"
    auth_allowed_emails: Annotated[list[str], NoDecode] = []

    @field_validator("auth_allowed_emails", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @field_validator("auth_allowed_domain", mode="before")
    @classmethod
    def _normalize_domain(cls, value):
        return value.strip().lower().lstrip("@") if isinstance(value, str) else value

    def is_allowed(self, email: str | None) -> bool:
        email = (email or "").strip().lower()
        if email.count("@") != 1:
            return False
        return email.endswith("@" + self.auth_allowed_domain) or email in self.auth_allowed_emails


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()


DEFAULT_OFFER_PERIOD_HOURS = "manhã=07:00-12:00,tarde=13:00-18:00,noite=19:00-23:00"


class OfferSettings(BaseSettings):
    """Horário que cada período de oferta (aula do semestre) ocupa a sala.

    A oferta só traz o nome do período (MANHÃ/TARDE/NOITE na planilha da UDF).
    Os horários padrão são provisórios, até virem do calendário acadêmico.

    Variável:
        OFFER_PERIOD_HOURS  "periodo=HH:MM-HH:MM,..." (padrão: DEFAULT_OFFER_PERIOD_HOURS)
    """

    model_config = SettingsConfigDict(extra="ignore", validate_default=True)

    offer_period_hours: Annotated[dict[str, tuple[time, time]], NoDecode] = DEFAULT_OFFER_PERIOD_HOURS

    @field_validator("offer_period_hours", mode="before")
    @classmethod
    def _parse(cls, value):
        if not isinstance(value, str):
            return value
        if not value.strip():
            # Vazio (`OFFER_PERIOD_HOURS=` no compose/.env) vale o padrão: antes
            # virava {} e nenhuma aula bloqueava sala, sem aviso.
            value = DEFAULT_OFFER_PERIOD_HOURS
        hours = {}
        for item in filter(None, (part.strip() for part in value.split(","))):
            name, _, span = item.partition("=")
            start, _, end = span.partition("-")
            start, end = time.fromisoformat(start.strip()), time.fromisoformat(end.strip())
            if not start < end:
                raise ValueError(f"OFFER_PERIOD_HOURS: início deve ser antes do fim em '{item}'")
            hours[name.strip().casefold()] = (start, end)
        return hours

    def hours_for(self, period_name: str | None) -> tuple[time, time] | None:
        """None = período desconhecido (ex.: "não se aplica"): não bloqueia sala."""
        return self.offer_period_hours.get((period_name or "").strip().casefold())


@lru_cache
def get_offer_settings() -> OfferSettings:
    return OfferSettings()
