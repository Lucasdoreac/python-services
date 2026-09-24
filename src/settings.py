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
"""
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
