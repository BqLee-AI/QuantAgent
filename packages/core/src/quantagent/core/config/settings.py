from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_SETTINGS_FILE = Path(__file__).resolve()


def _discover_repo_root(*, source_file: Path = _SETTINGS_FILE) -> Path | None:
    for parent in source_file.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "apps").is_dir() and (parent / "packages").is_dir():
            return parent
    return None


_SOURCE_REPO_ROOT = _discover_repo_root()


def _default_runtime_dir() -> Path:
    return (_SOURCE_REPO_ROOT / "runtime") if _SOURCE_REPO_ROOT is not None else Path("runtime")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str | None = None
    RUNTIME_DIR: Path = Field(default_factory=_default_runtime_dir)
    LOG_LEVEL: str = "INFO"
    MODEL_CONFIG_ENCRYPTION_KEY: str | None = None
    EVENT_BUS_BACKEND: str = "memory"
    EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS: str | None = None
    EVENT_BUS_KAFKA_CLIENT_ID: str = "quantagent-local"
    EVENT_BUS_KAFKA_DEFAULT_GROUP_ID: str = "quantagent-worker"
    EVENT_BUS_TOPIC_PREFIX: str = ""
    SCHEDULER_POLL_INTERVAL_SECONDS: float = 5.0
    SCHEDULER_DUE_LIMIT: int = 100
    SCHEDULER_RUN_TIMEOUT_MS: int | None = 30000

    @field_validator("RUNTIME_DIR", mode="before")
    @classmethod
    def normalize_runtime_dir(cls, value: str | Path | None) -> Path:
        if value in (None, ""):
            # 空字符串也视为未显式配置，避免把 `RUNTIME_DIR=` 误解析成当前目录并改变默认语义。
            return _default_runtime_dir()
        return Path(value)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()
