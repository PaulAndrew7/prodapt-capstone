import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize("field", ["llm_base_url", "llm_model", "llm_api_key"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_gateway_values_are_rejected(field: str, blank: str) -> None:
    values = dict(
        llm_provider="openai_compatible",
        llm_base_url="https://gateway.test/v1",
        llm_model="gpt-4o-mini",
        llm_api_key="test-key",
    )
    values[field] = blank
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)  # type: ignore[arg-type,call-arg]


@pytest.mark.parametrize(
    "url",
    [
        "ftp://gateway.test",
        "gateway.test/v1",
        "https://u:p@gateway.test/v1",
        "https://gateway.test/v1?key=secret",
        "https://gateway.test/v1#fragment",
        "https://gateway.test:invalid/v1",
        "https://gate way.test/v1",
    ],
)
def test_invalid_gateway_url_is_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(llm_base_url=url, _env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize("header", ["", "api key", "api-key\r\nInjected", "api:key"])
def test_invalid_gateway_header_is_rejected(header: str) -> None:
    with pytest.raises(ValidationError, match="LLM_API_KEY_HEADER"):
        Settings(llm_api_key_header=header, _env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "field", ["max_upload_bytes", "max_pdf_pages", "run_max_model_calls", "run_deadline_seconds"]
)
@pytest.mark.parametrize("value", [0, -1])
def test_operational_limits_must_be_positive(field: str, value: int) -> None:
    with pytest.raises(ValidationError, match=field):
        Settings(_env_file=None, **{field: value})  # type: ignore[arg-type,call-arg]


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


def test_provider_requires_base_url_model_and_key() -> None:
    with pytest.raises(ValidationError, match="LLM_BASE_URL, LLM_MODEL and LLM_API_KEY"):
        Settings(llm_provider="openai_compatible", _env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValidationError, match="LLM_BASE_URL"):
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            llm_provider="openai_compatible",
            llm_model="gpt-4o-mini",
            llm_api_key="k",
        )


def test_gateway_settings_build_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.workflow import llm

    s = Settings(  # type: ignore[call-arg]
        _env_file=None,
        llm_provider="openai_compatible",
        llm_base_url="https://gateway.example.test/v1",
        llm_model="gpt-4o-mini",
        llm_api_key="k",
        llm_json_mode="json_object",
    )
    monkeypatch.setattr(llm, "get_settings", lambda: s)
    llm.get_model_client.cache_clear()
    try:
        client = llm.get_model_client()
        assert isinstance(client, llm.GatewayModel)
        assert client.name == "gateway:gpt-4o-mini" and client.json_mode == "json_object"
    finally:
        llm.get_model_client.cache_clear()
