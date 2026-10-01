import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize("field", ["llm_base_url", "llm_api_key"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_gateway_values_are_rejected(field: str, blank: str) -> None:
    values = dict(
        llm_mode="required",
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
    with pytest.raises(ValidationError, match="LLM_API_KEY is required"):
        Settings(llm_mode="required", llm_provider="openai_compatible", _env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValidationError, match="LLM_API_KEY is required"):
        Settings(llm_mode="required", llm_provider="anthropic", _env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValidationError, match="requires LLM_MODEL"):
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            llm_mode="required",
            llm_provider="anthropic",
            llm_model=" ",
            llm_api_key="k",
        )
    with pytest.raises(ValidationError, match="LLM_BASE_URL"):
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            llm_mode="required",
            llm_provider="openai_compatible",
            llm_model="gpt-4o-mini",
            llm_api_key="k",
        )


def test_gateway_model_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    """The organizers' gateway picks the model itself, so none is configured or sent."""
    from app.workflow import llm

    s = Settings(  # type: ignore[call-arg]
        _env_file=None,
        llm_provider="openai_compatible",
        llm_base_url="https://gateway.example.test/v1",
        llm_model="",
        llm_api_key="k",
    )
    assert s.llm_model is None
    monkeypatch.setattr(llm, "get_settings", lambda: s)
    llm.get_model_client.cache_clear()
    try:
        client = llm.get_model_client()
        assert isinstance(client, llm.GatewayModel)
        assert client.model is None and client.name == "gateway:server-default"
    finally:
        llm.get_model_client.cache_clear()


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


def test_anthropic_settings_build_the_claude_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.workflow import llm
    from app.workflow.claude_model import ClaudeModel

    # No base URL is needed: the SDK's own endpoint is used.
    s = Settings(  # type: ignore[call-arg]
        _env_file=None,
        llm_provider="anthropic",
        llm_model="claude-sonnet-5-5",
        llm_api_key="k",
        llm_effort="low",
    )
    monkeypatch.setattr(llm, "get_settings", lambda: s)
    llm.get_model_client.cache_clear()
    try:
        client = llm.get_model_client()
        assert isinstance(client, ClaudeModel) and client.name == "anthropic:claude-sonnet-5-5"
        assert client.effort == "low"
    finally:
        llm.get_model_client.cache_clear()


@pytest.mark.parametrize("provider", ["anthropic", "openai_compatible"])
@pytest.mark.parametrize("key", [None, "", "   "])
def test_auto_mode_accepts_incomplete_provider_without_constructing_client(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    key: str | None,
) -> None:
    from app.workflow import llm

    settings = Settings(_env_file=None, llm_provider=provider, llm_api_key=key)  # type: ignore[arg-type,call-arg]
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    llm.get_model_client.cache_clear()
    try:
        assert llm.get_model_client() is None
    finally:
        llm.get_model_client.cache_clear()


def test_forced_offline_skips_client_construction_even_with_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workflow import llm

    settings = Settings(
        _env_file=None,
        llm_mode="offline",
        llm_provider="anthropic",
        llm_model="test-model",
        llm_api_key="test-key",
    )  # type: ignore[call-arg]
    monkeypatch.setattr(llm, "get_settings", lambda: settings)

    def unexpected() -> None:
        raise AssertionError("An offline request constructed a provider client")

    monkeypatch.setattr("app.workflow.claude_model.ClaudeModel", unexpected)
    llm.get_model_client.cache_clear()
    try:
        assert llm.get_model_client() is None
    finally:
        llm.get_model_client.cache_clear()
