from pydantic_settings import SettingsConfigDict

from quantagent.core.config.settings import Settings as CoreSettings


class Settings(CoreSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

settings = Settings()
