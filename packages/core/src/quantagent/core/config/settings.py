from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_SETTINGS_FILE = Path(__file__).resolve()


def _discover_repo_root(*, source_file: Path = _SETTINGS_FILE) -> Path | None:
    for parent in source_file.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "apps").is_dir() and (parent / "packages").is_dir():
            return parent
    return None


_SOURCE_REPO_ROOT = _discover_repo_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str | None = None
    RUNTIME_DIR: Path | None = None
    LOG_LEVEL: str = "INFO"
    MODEL_CONFIG_ENCRYPTION_KEY: str | None = None

    @field_validator("RUNTIME_DIR", mode="before")
    @classmethod
    def normalize_runtime_dir(cls, value: str | Path | None) -> Path | None:
        if value in (None, ""):
            return None
        return Path(value)

    def model_post_init(self, __context: object) -> None:
        if self.RUNTIME_DIR is not None:
            return
        # 空字符串也视为未显式配置，避免把 `RUNTIME_DIR=` 误解析成当前目录并改变默认语义。
        self.RUNTIME_DIR = (_SOURCE_REPO_ROOT / "runtime") if _SOURCE_REPO_ROOT is not None else Path("runtime")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()
