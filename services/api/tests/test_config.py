import pytest
from pydantic import ValidationError

from app.config import Settings


def test_development_defaults_are_valid() -> None:
    s = Settings(app_env="development", _env_file=None)  # type: ignore[call-arg]
    assert s.auth_mode == "demo"
    assert s.llm_provider == "none"


def test_production_rejects_development_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as exc:
        Settings(app_env="production", _env_file=None)  # type: ignore[call-arg]
    message = str(exc.value)
    assert "DATABASE_URL" in message
    assert "SESSION_SECRET" in message
    assert "AUTH_MODE=demo" in message


def test_production_accepts_explicit_config() -> None:
    s = Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env="production",
        database_url="postgresql+psycopg://u:p@db:5432/clause",
        session_secret="x" * 40,
        auth_mode="session",
    )
    assert s.app_env == "production"


def test_provider_requires_model_and_key() -> None:
    with pytest.raises(ValidationError, match="LLM_MODEL and LLM_API_KEY"):
        Settings(llm_provider="anthropic", _env_file=None)  # type: ignore[call-arg]
