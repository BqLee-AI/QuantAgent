from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from quantagent.core.config.settings import Settings as CoreSettings


class Settings(CoreSettings):
    """在通用核心配置之上补充 API 运行时配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    AUTH_ENABLED: bool = True
    AUTH_ADMIN_PASSWORD: str | None = None
    AUTH_SESSION_SECRET: str | None = None
    AUTH_COOKIE_NAME: str = "quantagent_session"
    AUTH_COOKIE_SECURE: bool | None = None
    AUTH_COOKIE_SAME_SITE: Literal["lax", "strict", "none"] = "lax"
    AUTH_SESSION_LIFETIME_SECONDS: int = Field(default=43200, ge=300)
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

        # 未显式配置时按环境推导 cookie secure，production 默认必须收紧。
        if self.AUTH_COOKIE_SECURE is None:
            self.AUTH_COOKIE_SECURE = self.is_production

        if self.AUTH_COOKIE_SAME_SITE == "none" and not self.AUTH_COOKIE_SECURE:
            raise ValueError("AUTH_COOKIE_SAME_SITE=none requires AUTH_COOKIE_SECURE=true")

        if not self.AUTH_ENABLED and environment != "development":
            raise ValueError("AUTH_ENABLED=false is only allowed when APP_ENV=development")

        # 只有 development/test/local 才自动兜底弱默认；staging 等环境必须显式提供。
        # production 仍会额外做强校验，拒绝弱默认和关闭鉴权。
        is_dev_or_test = environment in {"development", "test", "local"}

        if not self.AUTH_ADMIN_PASSWORD:
            if is_dev_or_test:
                self.AUTH_ADMIN_PASSWORD = "dev-admin-password"
            elif not self.is_production:
                raise ValueError("AUTH_ADMIN_PASSWORD is required when APP_ENV is not development/test/local")

        if not self.AUTH_SESSION_SECRET:
            if is_dev_or_test:
                self.AUTH_SESSION_SECRET = "dev-session-secret-change-me"
            elif not self.is_production:
                raise ValueError("AUTH_SESSION_SECRET is required when APP_ENV is not development/test/local")

        # production 不允许弱默认或关闭鉴权，避免部署时静默裸奔。
        if self.is_production:
            if not self.AUTH_COOKIE_SECURE:
                raise ValueError("Production session cookie must be secure")
            if not self.AUTH_ADMIN_PASSWORD:
                raise ValueError("AUTH_ADMIN_PASSWORD is required in production")
            if not self.AUTH_SESSION_SECRET:
                raise ValueError("AUTH_SESSION_SECRET is required in production")
            if self.AUTH_ADMIN_PASSWORD == "dev-admin-password":
                raise ValueError("Production must not use the development auth password default")
            if self.AUTH_SESSION_SECRET == "dev-session-secret-change-me":
                raise ValueError("Production must not use the development session secret default")

        return self


settings = Settings()
