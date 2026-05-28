from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from quantagent.core.config.settings import Settings as CoreSettings

_SETTINGS_FILE = Path(__file__).resolve()
_CWD = Path.cwd()
_PLACEHOLDER_SECRETS = {
    "12345678",
    "change-me",
    "changeme",
    "dev-session-secret-change-me",
    "please-change-me",
}
_WEAK_AUTH_PASSWORDS = _PLACEHOLDER_SECRETS | {
    "admin",
    "admin123",
    "password",
    "password123",
    "prod-password",
    "staging-password",
}
_WEAK_SESSION_SECRET_VALUES = _PLACEHOLDER_SECRETS | {
    "dev-session-secret",
    "dev-session-secret-change-me",
    "session-secret",
}
_MIN_NON_DEV_AUTH_PASSWORD_LENGTH = 12
_MIN_NON_DEV_SESSION_SECRET_LENGTH = 32


def _dedupe_paths(paths: list[Path]) -> tuple[Path, ...]:
    return tuple(dict.fromkeys(paths))


def _discover_source_layout(*, source_file: Path = _SETTINGS_FILE) -> tuple[Path | None, Path | None]:
    for parent in source_file.parents:
        api_dir = parent / "apps/api"
        if api_dir.is_dir() and (parent / "pyproject.toml").is_file():
            return parent, api_dir
    return None, None


_SOURCE_REPO_ROOT, _SOURCE_API_APP_DIR = _discover_source_layout()


def _resolve_env_roots(
    *,
    cwd: Path,
    source_repo_root: Path | None = _SOURCE_REPO_ROOT,
    source_api_app_dir: Path | None = _SOURCE_API_APP_DIR,
) -> tuple[Path | None, Path | None]:
    if source_repo_root is not None and source_api_app_dir is not None:
        source_api_dir = source_repo_root / "apps/api"
        if source_api_dir == source_api_app_dir:
            return source_repo_root, source_api_app_dir

    cwd_api_dir = cwd / "apps/api"
    if cwd_api_dir.is_dir():
        return cwd, cwd_api_dir

    if cwd.name == "api" and cwd.parent.name == "apps":
        return cwd.parents[1], cwd

    if source_repo_root is not None and source_api_app_dir is not None:
        return source_repo_root, source_api_app_dir

    return None, None


def _base_env_files(
    *,
    cwd: Path = _CWD,
    source_repo_root: Path | None = _SOURCE_REPO_ROOT,
    source_api_app_dir: Path | None = _SOURCE_API_APP_DIR,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    repo_root_dir, api_app_dir = _resolve_env_roots(
        cwd=cwd,
        source_repo_root=source_repo_root,
        source_api_app_dir=source_api_app_dir,
    )
    root_env = repo_root_dir / ".env" if repo_root_dir is not None else None
    api_env = api_app_dir / ".env" if api_app_dir is not None else None
    api_local_env = api_app_dir / ".env.local" if api_app_dir is not None else None

    if root_env is not None:
        candidates.append(root_env)

    cwd_env = cwd / ".env"
    if cwd_env not in {root_env, api_env}:
        candidates.append(cwd_env)

    if api_env is not None and api_local_env is not None:
        candidates.extend((api_env, api_local_env))
    return _dedupe_paths(candidates)


def _resolve_app_env_from_files(env_files: tuple[Path, ...]) -> str | None:
    app_env: str | None = None
    for env_file in env_files:
        if not env_file.is_file():
            continue
        value = dotenv_values(env_file).get("APP_ENV")
        if value:
            app_env = str(value).strip()
    return app_env or None


def _build_env_file_paths(
    *,
    app_env: str | None = None,
    cwd: Path = _CWD,
    source_repo_root: Path | None = _SOURCE_REPO_ROOT,
    source_api_app_dir: Path | None = _SOURCE_API_APP_DIR,
) -> tuple[Path, ...]:
    repo_root_dir, api_app_dir = _resolve_env_roots(
        cwd=cwd,
        source_repo_root=source_repo_root,
        source_api_app_dir=source_api_app_dir,
    )
    base_files = _base_env_files(
        cwd=cwd,
        source_repo_root=source_repo_root,
        source_api_app_dir=source_api_app_dir,
    )
    # APP_ENV controls which API-specific dotenv gets loaded; process env wins,
    # then base dotenv layers decide before environment-specific files are appended.
    selected_env = (app_env or _resolve_app_env_from_files(base_files) or "").strip().lower()
    candidates = list(base_files)
    if selected_env and api_app_dir is not None:
        candidates.extend((api_app_dir / f".env.{selected_env}", api_app_dir / f".env.{selected_env}.local"))
    return _dedupe_paths(candidates)


def _build_env_files() -> tuple[str, ...]:
    return tuple(str(path) for path in _build_env_file_paths(app_env=os.environ.get("APP_ENV")))


# Default settings are built at import time so process-level APP_ENV can select
# the right dotenv matrix before the shared singleton below is created.
_ENV_FILES = _build_env_files()


class Settings(CoreSettings):
    """在通用核心配置之上补充 API 运行时配置。"""

    model_config = SettingsConfigDict(
        # API dotenv uses root defaults first, then API-specific and
        # environment-specific files; process environment still wins.
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

        is_dev_or_test = environment in {"development", "test", "local"}

        if not self.AUTH_ENABLED and not is_dev_or_test:
            raise ValueError("AUTH_ENABLED=false is only allowed when APP_ENV is development/test/local")

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

        if not is_dev_or_test:
            if self.AUTH_ADMIN_PASSWORD and self.AUTH_ADMIN_PASSWORD.lower() in _PLACEHOLDER_SECRETS:
                raise ValueError("AUTH_ADMIN_PASSWORD must not use a placeholder value outside development/test/local")
            if self.AUTH_SESSION_SECRET and self.AUTH_SESSION_SECRET.lower() in _PLACEHOLDER_SECRETS:
                raise ValueError("AUTH_SESSION_SECRET must not use a placeholder value outside development/test/local")
            if self.AUTH_ADMIN_PASSWORD and (
                len(self.AUTH_ADMIN_PASSWORD) < _MIN_NON_DEV_AUTH_PASSWORD_LENGTH
                or self.AUTH_ADMIN_PASSWORD.lower() in _WEAK_AUTH_PASSWORDS
            ):
                raise ValueError("AUTH_ADMIN_PASSWORD must be at least 12 characters and not use a common weak value outside development/test/local")
            if self.AUTH_SESSION_SECRET and (
                len(self.AUTH_SESSION_SECRET) < _MIN_NON_DEV_SESSION_SECRET_LENGTH
                or self.AUTH_SESSION_SECRET.lower() in _WEAK_SESSION_SECRET_VALUES
            ):
                raise ValueError("AUTH_SESSION_SECRET must be at least 32 characters and not look like a development placeholder outside development/test/local")

        return self


settings = Settings()
