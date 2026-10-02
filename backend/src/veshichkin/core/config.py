from functools import lru_cache
from pathlib import Path

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VESHICHKIN_")

    application_name: str = "Veshichkin"
    environment: str = "development"
    debug: bool = False
    static_dir: Path | None = None
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://veshichkin@localhost:5432/veshichkin"
    )

    @field_validator("database_url")
    @classmethod
    def require_psycopg(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+psycopg":
            raise ValueError("Use a PostgreSQL DSN with the postgresql+psycopg scheme")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
