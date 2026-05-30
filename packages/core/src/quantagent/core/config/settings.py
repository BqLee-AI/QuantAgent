from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str | None = None
    RUNTIME_DIR: Path = Path("runtime")
    LOG_LEVEL: str = "INFO"
    MODEL_CONFIG_ENCRYPTION_KEY: str | None = None
    EVENT_BUS_BACKEND: str = "memory"
    EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS: str | None = None
    EVENT_BUS_KAFKA_CLIENT_ID: str = "quantagent-local"
    EVENT_BUS_KAFKA_DEFAULT_GROUP_ID: str = "quantagent-worker"
    EVENT_BUS_TOPIC_PREFIX: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()
