from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FullFit API"
    environment: Literal["development", "test", "production"] = "development"

    # Banco
    database_url: str
    test_database_url: str | None = None

    # Autenticação
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    email_verification_token_expire_hours: int = Field(default=24, gt=0)
    password_reset_token_expire_minutes: int = Field(default=30, gt=0)
    # Qual implementação de EmailSender usar (veja app/core/email.py). Hoje só existe a
    # de console; adicione um provedor real lá e o nome dele aqui.
    email_backend: Literal["console"] = "console"
    password_min_length: int = Field(default=8, ge=1)
    password_max_length: int = Field(default=128, ge=1)

    # Versão dos documentos legais aceitos no cadastro
    consent_terms_version: str = Field(default="1.0", min_length=1, max_length=10)
    consent_privacy_version: str = Field(default="1.0", min_length=1, max_length=10)
    consent_advertising_version: str = Field(default="1.0", min_length=1, max_length=10)

    @field_validator("database_url", "test_database_url")
    @classmethod
    def exigir_driver_asyncpg(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("postgresql+asyncpg://"):
            raise ValueError("A URL do banco deve começar com postgresql+asyncpg://")
        return v

    @model_validator(mode="after")
    def validate_password_limits(self) -> Self:
        if self.password_min_length > self.password_max_length:
            raise ValueError("PASSWORD_MIN_LENGTH não pode ser maior que PASSWORD_MAX_LENGTH")
        return self


settings = Settings()