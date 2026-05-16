from pydantic_settings import SettingsConfigDict

from quantagent.core.config.settings import Settings as CoreSettings


class Settings(CoreSettings):
    """在通用核心配置之上补充 API 运行时配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000


settings = Settings()
