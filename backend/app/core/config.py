"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / ".env"), env_prefix="", extra="ignore")

    app_env: str = Field("development", alias="TRACETEST_ENV")
    data_dir: Path = Field(REPO_ROOT / "var", alias="TRACETEST_DATA_DIR")
    secret_key: str = Field("change-me-in-env", alias="TRACETEST_SECRET_KEY")
    session_hours: int = Field(12, alias="TRACETEST_SESSION_HOURS")
    cookie_secure: bool = Field(False, alias="TRACETEST_COOKIE_SECURE")
    cors_origins: str = Field("http://localhost:5173", alias="TRACETEST_CORS_ORIGINS")
    seed_on_startup: bool = Field(True, alias="TRACETEST_SEED_ON_STARTUP")
    rate_limit_per_minute: int = Field(600, alias="TRACETEST_RATE_LIMIT_PER_MINUTE")

    admin_email: str = Field("admin@northwind-hcm.example", alias="TRACETEST_ADMIN_EMAIL")
    admin_password: str | None = Field(None, alias="TRACETEST_ADMIN_PASSWORD")
    qa_email: str = Field("qa.engineer@northwind-hcm.example", alias="TRACETEST_QA_EMAIL")
    qa_password: str | None = Field(None, alias="TRACETEST_QA_PASSWORD")
    reviewer_email: str = Field("reviewer@northwind-hcm.example", alias="TRACETEST_REVIEWER_EMAIL")
    reviewer_password: str | None = Field(None, alias="TRACETEST_REVIEWER_PASSWORD")

    # LLM providers
    llm_mode: str = Field("live", alias="TRACETEST_LLM_MODE")  # live | mock
    groq_api_key: str | None = Field(None, alias="GROQ_API_KEY")
    groq_api_key2: str | None = Field(None, alias="GROQ_API_KEY2")
    groq_api_key3: str | None = Field(None, alias="GROQ_API_KEY3")
    groq_key: str | None = Field(None, alias="GROQ_KEY")
    groq_key2: str | None = Field(None, alias="GROQ_KEY2")
    groq_key3: str | None = Field(None, alias="GROQ_KEY3")
    groq_model: str = Field("openai/gpt-oss-120b", alias="GROQ_MODEL")
    groq_base_url: str = Field("https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")

    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    gemini_api_key2: str | None = Field(None, alias="GEMINI_API_KEY2")
    gemini_api_key3: str | None = Field(None, alias="GEMINI_API_KEY3")
    gemini_key: str | None = Field(None, alias="GEMINI_KEY")
    gemini_key2: str | None = Field(None, alias="GEMINI_KEY2")
    gemini_key3: str | None = Field(None, alias="GEMINI_KEY3")
    gemini_model: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL")

    ollama_base_url: str | None = Field(None, alias="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3.1", alias="OLLAMA_MODEL")
    llm_timeout_seconds: float = Field(60, alias="TRACETEST_LLM_TIMEOUT")
    llm_max_retries: int = Field(2, alias="TRACETEST_LLM_MAX_RETRIES")

    @property
    def groq_keys(self) -> list[str]:
        res: list[str] = []
        for val in (self.groq_api_key, self.groq_key, self.groq_api_key2, self.groq_key2, self.groq_api_key3, self.groq_key3):
            if val and val.strip() and val.strip() not in res:
                res.append(val.strip())
        return res

    @property
    def gemini_keys(self) -> list[str]:
        res: list[str] = []
        for val in (self.gemini_api_key, self.gemini_key, self.gemini_api_key2, self.gemini_key2, self.gemini_api_key3, self.gemini_key3):
            if val and val.strip() and val.strip() not in res:
                res.append(val.strip())
        return res

    # Execution sandbox
    exec_timeout_seconds: int = Field(60, alias="TRACETEST_EXEC_TIMEOUT")
    exec_max_output_bytes: int = Field(256_000, alias="TRACETEST_EXEC_MAX_OUTPUT")
    exec_memory_mb: int = Field(512, alias="TRACETEST_EXEC_MEMORY_MB")
    playwright_target_url: str | None = Field(None, alias="TRACETEST_PLAYWRIGHT_TARGET_URL")
    chromium_executable: str | None = Field("/usr/bin/chromium", alias="TRACETEST_CHROMIUM_EXECUTABLE")

    # GitHub
    github_token: str | None = Field(None, alias="GITHUB_TOKEN")
    github_api_url: str = Field("https://api.github.com", alias="GITHUB_API_URL")

    @field_validator("data_dir", mode="after")
    @classmethod
    def _absolute(cls, v: Path) -> Path:
        return v if v.is_absolute() else (REPO_ROOT / v).resolve()

    @property
    def db_path(self) -> Path:
        return self.data_dir / "tracetest.db"

    @property
    def checkpoint_db_path(self) -> Path:
        return self.data_dir / "workflow_checkpoints.db"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def is_dev(self) -> bool:
        return self.app_env in ("development", "test")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    for d in (s.data_dir, s.artifacts_dir, s.uploads_dir, s.backups_dir):
        d.mkdir(parents=True, exist_ok=True)
    return s
