from typing import Literal

from pydantic import Field, field_validator
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

    @field_validator("database_url", "test_database_url")
    @classmethod
    def exigir_driver_asyncpg(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("postgresql+asyncpg://"):
            raise ValueError("A URL do banco deve começar com postgresql+asyncpg://")
        return v


settings = Settings()  # type: ignore[call-arg]