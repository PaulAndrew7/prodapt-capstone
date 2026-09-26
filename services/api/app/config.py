"""Validated runtime configuration.

Values come from environment variables (or a local `.env`). Production refuses to start
with development defaults; see `.env.example` at the repository root for every setting.
Provider credentials stay server-side and are never sent to the web client.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    session_secret: SecretStr = SecretStr(DEV_SESSION_SECRET)
    # "demo" resolves every request to the seeded demo admin. Production requires "session".
    auth_mode: Literal["demo", "session"] = "demo"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Original policy files, parse artifacts and generated reports.
    storage_dir: Path = REPO_ROOT / "var" / "storage"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 200

    # Local embeddings (plan §4.1). The fastembed build of bge-small-en-v1.5 is recorded
    # with every chunk so an index revision can be reproduced.
    embeddings_enabled: bool = True
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    model_cache_dir: Path = REPO_ROOT / "var" / "models"

    # Runtime language model. Unset until F08 selects and benchmarks one; no default model
    # is imposed. The key is read server-side only.
    llm_provider: Literal["none", "anthropic", "openai"] = "none"
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    run_max_model_calls: int = 8
    run_deadline_seconds: int = 120

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.llm_provider != "none" and (not self.llm_model or self.llm_api_key is None):
            raise ValueError("LLM_PROVIDER is set, so LLM_MODEL and LLM_API_KEY are required")
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
