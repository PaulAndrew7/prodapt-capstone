"""Validated runtime configuration.

Values come from environment variables (or a local `.env`). Production refuses to start
with development defaults; see `.env.example` at the repository root for every setting.
Provider credentials stay server-side and are never sent to the web client.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_DATABASE_URL = "postgresql+psycopg://clause:clause@localhost:5433/clause"
DEV_SESSION_SECRET = "dev-only-session-secret-change-me"  # noqa: S105 - rejected in production

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = DEV_DATABASE_URL
    # Data directory of the local PostgreSQL that `python -m app.cli db-start` runs.
    local_db_dir: Path = REPO_ROOT / "var" / "postgres"
    session_secret: SecretStr = SecretStr(DEV_SESSION_SECRET)
    # "demo" resolves every request to the seeded demo admin. Production requires "session".
    auth_mode: Literal["demo", "session"] = "demo"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Original policy files, parse artifacts and generated reports.
    storage_dir: Path = REPO_ROOT / "var" / "storage"
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    max_pdf_pages: int = Field(default=200, gt=0)

    # Local embeddings (plan §4.1). The fastembed build of bge-small-en-v1.5 is recorded
    # with every chunk so an index revision can be reproduced.
    embeddings_enabled: bool = True
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    model_cache_dir: Path = REPO_ROOT / "var" / "models"

    # Runtime language model (plan §4.4): GPT-4o mini through the organizers' gateway, which
    # is expected to speak the OpenAI chat-completions format. Unset means assessments and
    # lookups are refused with a clear error. The key is read server-side only.
    llm_provider: Literal["none", "openai_compatible"] = "none"
    llm_base_url: str | None = None  # the gateway base URL; no default is guessed
    llm_model: str | None = None  # gpt-4o-mini or the gateway's alias for it
    llm_api_key: SecretStr | None = None
    # Unset sends `Authorization: Bearer <key>`; a name such as `api-key` sends the key there.
    llm_api_key_header: str | None = None
    # json_schema constrains replies to each stage's schema; json_object is the fallback for
    # gateways without schema support (the reply is validated the same way).
    llm_json_mode: Literal["json_schema", "json_object"] = "json_schema"
    llm_temperature: float | None = None  # unset uses the model default
    run_max_model_calls: int = Field(default=8, gt=0)
    run_deadline_seconds: int = Field(default=120, gt=0)

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.llm_provider != "none" and not (
            self.llm_base_url
            and self.llm_base_url.strip()
            and self.llm_model
            and self.llm_model.strip()
            and self.llm_api_key is not None
            and self.llm_api_key.get_secret_value().strip()
        ):
            raise ValueError(
                "LLM_PROVIDER is set, so LLM_BASE_URL, LLM_MODEL and LLM_API_KEY are required"
            )
        if self.llm_base_url:
            url = urlsplit(self.llm_base_url)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.query
                or url.fragment
                or any(c.isspace() for c in self.llm_base_url)
            ):
                raise ValueError(
                    "LLM_BASE_URL must be an HTTP(S) base URL "
                    "without credentials, query or fragment"
                )
            try:
                _ = url.port
            except ValueError as exc:
                raise ValueError("LLM_BASE_URL has an invalid port") from exc
        if self.llm_api_key_header is not None and not re.fullmatch(
            r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", self.llm_api_key_header
        ):
            raise ValueError("LLM_API_KEY_HEADER must be a valid HTTP header name")
        if self.app_env != "production":
            return self
        problems = []
        if self.database_url == DEV_DATABASE_URL:
            problems.append("DATABASE_URL must be set explicitly")
        if self.session_secret.get_secret_value() == DEV_SESSION_SECRET:
            problems.append("SESSION_SECRET must be set to a unique secret")
        if len(self.session_secret.get_secret_value()) < 32:
            problems.append("SESSION_SECRET must be at least 32 characters")
        if self.auth_mode != "session":
            problems.append("AUTH_MODE=demo is not allowed in production")
        if problems:
            raise ValueError("Invalid production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
