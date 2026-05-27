from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from quantagent.core.config.settings import Settings as CoreSettings


_API_APP_DIR = Path(__file__).resolve().parents[4]
_REPO_ROOT_DIR = Path(__file__).resolve().parents[6]
_CWD = Path.cwd()
_ENV_FILES = (
    str(_REPO_ROOT_DIR / ".env"),
    str(_CWD / ".env"),
    str(_CWD / "apps/api/.env"),
    str(_API_APP_DIR / ".env"),
)


class Settings(CoreSettings):
    """在通用核心配置之上补充 API 运行时配置。"""

    model_config = SettingsConfigDict(
        # 共享变量放仓库根目录 .env，API 私有变量放 apps/api/.env。
        # 源码路径和当前工作目录都纳入候选，兼容源码开发与根目录运行。
        env_file=_ENV_FILES,
        extra="ignore",
    )

    API_V1_PREFIX: str = "/api/v1"
    API_HOST: str = Field(default="127.0.0.1", validation_alias=AliasChoices("API_HOST", "HOST"))
    API_PORT: int = Field(default=8000, validation_alias=AliasChoices("API_PORT", "PORT"))
    AUTH_ENABLED: bool = True
    AUTH_ADMIN_PASSWORD: str | None = None
    AUTH_SESSION_SECRET: str | None = None
    AUTH_COOKIE_NAME: str = "quantagent_session"
    AUTH_COOKIE_SECURE: bool | None = None
    AUTH_COOKIE_SAME_SITE: Literal["lax", "strict", "none"] = "lax"
    AUTH_SESSION_LIFETIME_SECONDS: int = Field(default=43200, ge=300)
    AUTH_SESSION_ABSOLUTE_LIFETIME_SECONDS: int = Field(default=86400, ge=300)
    AUTH_SESSION_REFRESH_THRESHOLD_SECONDS: int = Field(default=1800, ge=0)
    AUTH_CSRF_HEADER_NAME: str = "X-CSRF-Token"

    @field_validator("AUTH_COOKIE_SAME_SITE", mode="before")
    @classmethod
    def normalize_same_site(cls, value: str | None) -> str:
        return str(value or "lax").lower()

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        environment = self.APP_ENV.lower()

        if self.AUTH_ADMIN_PASSWORD is not None:
            self.AUTH_ADMIN_PASSWORD = self.AUTH_ADMIN_PASSWORD.strip()
        if self.AUTH_SESSION_SECRET is not None:
            self.AUTH_SESSION_SECRET = self.AUTH_SESSION_SECRET.strip()

        if self.AUTH_COOKIE_SECURE is None:
            self.AUTH_COOKIE_SECURE = self.is_production

        if self.AUTH_COOKIE_SAME_SITE == "none" and not self.AUTH_COOKIE_SECURE:
            raise ValueError("AUTH_COOKIE_SAME_SITE=none requires AUTH_COOKIE_SECURE=true")

        if not self.AUTH_ENABLED and environment != "development":
            raise ValueError("AUTH_ENABLED=false is only allowed when APP_ENV=development")

        is_dev_or_test = environment in {"development", "test", "local"}

        if not self.AUTH_ADMIN_PASSWORD:
            if is_dev_or_test:
                self.AUTH_ADMIN_PASSWORD = "12345678"
            elif not self.is_production:
                raise ValueError("AUTH_ADMIN_PASSWORD is required when APP_ENV is not development/test/local")

        if not self.AUTH_SESSION_SECRET:
            if is_dev_or_test:
                self.AUTH_SESSION_SECRET = "dev-session-secret-change-me"
            elif not self.is_production:
                raise ValueError("AUTH_SESSION_SECRET is required when APP_ENV is not development/test/local")

        if self.is_production:
            if not self.AUTH_COOKIE_SECURE:
                raise ValueError("Production session cookie must be secure")
            if not self.AUTH_ADMIN_PASSWORD:
                raise ValueError("AUTH_ADMIN_PASSWORD is required in production")
            if not self.AUTH_SESSION_SECRET:
                raise ValueError("AUTH_SESSION_SECRET is required in production")
            if self.AUTH_ADMIN_PASSWORD == "12345678":
                raise ValueError("Production must not use the development auth password default")
            if self.AUTH_SESSION_SECRET == "dev-session-secret-change-me":
                raise ValueError("Production must not use the development session secret default")

        return self


settings = Settings()
