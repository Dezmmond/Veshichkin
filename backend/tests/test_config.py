import os

import pytest
from pydantic import ValidationError

from veshichkin.core.config import Settings


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in os.environ:
        if name.startswith("VESHICHKIN_"):
            monkeypatch.delenv(name)


def test_defaults() -> None:
    settings = Settings()
    assert settings.application_name == "Veshichkin"
    assert settings.environment == "development"
    assert settings.debug is False
    assert str(settings.database_url) == (
        "postgresql+psycopg://veshichkin@localhost:5432/veshichkin"
    )
    assert settings.database_url.hosts()[0]["password"] is None


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "postgresql+psycopg://test_user:test_password@db.example:5432/test_db"
    monkeypatch.setenv("VESHICHKIN_DATABASE_URL", url)
    monkeypatch.setenv("VESHICHKIN_APPLICATION_NAME", "Test app")
    monkeypatch.setenv("VESHICHKIN_ENVIRONMENT", "test")
    monkeypatch.setenv("VESHICHKIN_DEBUG", "true")
    settings = Settings()
    assert str(settings.database_url) == url
    assert settings.application_name == "Test app"
    assert settings.environment == "test"
    assert settings.debug is True


@pytest.mark.parametrize("url", ["sqlite:///test.db", "postgresql+asyncpg://user@localhost/db"])
def test_rejects_unsupported_database_driver(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=url)
