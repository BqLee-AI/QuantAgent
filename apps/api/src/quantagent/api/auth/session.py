from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json

from fastapi import Depends, Request, Response

from quantagent.api.auth.actor import (
    ALL_CAPABILITIES,
    DEVELOPMENT_BYPASS_CSRF_TOKEN,
    LOCAL_ACTOR_TYPE,
    LOCAL_ADMIN_ACTOR_ID,
    LOCAL_DEV_ACTOR_ID,
    CurrentActor,
)
from quantagent.api.config.settings import Settings
from quantagent.api.http.errors import UnauthorizedError


def _hmac_sha256(secret: str, value: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _session_signature(secret: str, payload_json: str) -> str:
    """对规范化后的 session payload 签名，避免客户端篡改 cookie 内容。"""
    return _hmac_sha256(secret, payload_json)


def _csrf_token(secret: str, actor_id: str, expires_at: int) -> str:
    """从 session secret、actor 和过期时间派生稳定 CSRF token。"""
    return _hmac_sha256(secret, f"csrf:{actor_id}:{expires_at}")


def _compare_sensitive_text(left: str, right: str) -> bool:
    """用 UTF-8 bytes 做常量时间比较，避免非 ASCII 字符触发 TypeError。"""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _b64encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _b64decode(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")


def _serialize_session(payload: dict[str, object], secret: str) -> str:
    """把 session payload 编码成 cookie 安全字符串，并附带 HMAC 签名。"""
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = _session_signature(secret, payload_json)
    return f"{_b64encode(payload_json)}.{signature}"


def _deserialize_session(raw_session: str, secret: str) -> dict[str, object]:
    """解析并校验 session cookie；任何格式或签名问题都按未授权处理。"""
    try:
        encoded_payload, signature = raw_session.rsplit(".", 1)
    except ValueError as exc:
        raise UnauthorizedError() from exc

    try:
        payload_json = _b64decode(encoded_payload)
    except Exception as exc:
        raise UnauthorizedError() from exc

    expected_signature = _session_signature(secret, payload_json)
    if not _compare_sensitive_text(signature, expected_signature):
        raise UnauthorizedError()

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise UnauthorizedError() from exc

    if not isinstance(payload, dict):
        raise UnauthorizedError()

    return payload


def issue_session(
    actor_id: str,
    app_settings: Settings,
    *,
    capabilities: frozenset[str] | None = None,
    expires_at: int | None = None,
) -> tuple[str, str]:
    """签发本地单用户 session，并返回给前端 bootstrap 用的 CSRF token。"""
    if actor_id != LOCAL_ADMIN_ACTOR_ID:
        raise ValueError(f"Unsupported actor_id for session issuance: {actor_id}")

    capability_set = ALL_CAPABILITIES if capabilities is None else capabilities
    if not capability_set or not capability_set.issubset(ALL_CAPABILITIES):
        raise ValueError("capabilities must be a non-empty subset of ALL_CAPABILITIES")
    session_expires_at = expires_at if expires_at is not None else int(
        (datetime.now(UTC) + timedelta(seconds=app_settings.AUTH_SESSION_LIFETIME_SECONDS)).timestamp()
    )
    csrf_token = _csrf_token(app_settings.AUTH_SESSION_SECRET or "", actor_id, session_expires_at)
    payload = {
        "sub": actor_id,
        "type": LOCAL_ACTOR_TYPE,
        "exp": session_expires_at,
        "csrf": csrf_token,
        "capabilities": sorted(capability_set),
    }
    return _serialize_session(payload, app_settings.AUTH_SESSION_SECRET or ""), csrf_token


def refresh_session(
    actor: "CurrentActor",
    app_settings: Settings,
    *,
    expires_at: int | None = None,
) -> tuple[str, str]:
    """基于当前 actor 能力集重签 session，用于活动续期。"""
    return issue_session(
        actor.actor_id,
        app_settings,
        capabilities=actor.capabilities,
        expires_at=expires_at,
    )


def clear_session_cookie(response: Response, app_settings: Settings) -> None:
    """按当前 cookie 配置清除登录态，logout 和 development bypass login 共用。"""
    response.delete_cookie(
        key=app_settings.AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=bool(app_settings.AUTH_COOKIE_SECURE),
        samesite=app_settings.AUTH_COOKIE_SAME_SITE,
    )


def set_session_cookie(response: Response, session_value: str, app_settings: Settings) -> None:
    """写入 HttpOnly session cookie，避免前端 JavaScript 读取 session 原文。"""
    response.set_cookie(
        key=app_settings.AUTH_COOKIE_NAME,
        value=session_value,
        max_age=app_settings.AUTH_SESSION_LIFETIME_SECONDS,
        path="/",
        httponly=True,
        secure=bool(app_settings.AUTH_COOKIE_SECURE),
        samesite=app_settings.AUTH_COOKIE_SAME_SITE,
    )


def authenticate_admin_password(password: str, app_settings: Settings) -> None:
    """校验本地管理员口令；失败时不暴露口令来源或匹配细节。"""
    expected_password = app_settings.AUTH_ADMIN_PASSWORD or ""
    if not _compare_sensitive_text(password, expected_password):
        raise UnauthorizedError()


def development_bypass_actor() -> CurrentActor:
    """development 关闭鉴权时仍返回稳定 actor，保证审计字段不为空。"""
    return CurrentActor(
        actor_id=LOCAL_DEV_ACTOR_ID,
        actor_type=LOCAL_ACTOR_TYPE,
        capabilities=ALL_CAPABILITIES,
        csrf_token=DEVELOPMENT_BYPASS_CSRF_TOKEN,
        auth_mode="development_bypass",
    )


def resolve_current_actor(request: Request) -> CurrentActor:
    """统一解析当前 actor；业务 route 应复用该 dependency，而不是自行读 cookie。"""
    app_settings: Settings = request.app.state.settings

    if not app_settings.AUTH_ENABLED:
        return development_bypass_actor()

    raw_session = request.cookies.get(app_settings.AUTH_COOKIE_NAME)
    if not raw_session:
        raise UnauthorizedError()

    payload = _deserialize_session(raw_session, app_settings.AUTH_SESSION_SECRET or "")
    actor_id = payload.get("sub")
    actor_type = payload.get("type")
    expires_at = payload.get("exp")
    capabilities = payload.get("capabilities")
    csrf_token = payload.get("csrf")

    # session payload 只接受当前单用户模型和集中维护的 capability 集合。
    if actor_id != LOCAL_ADMIN_ACTOR_ID or actor_type != LOCAL_ACTOR_TYPE:
        raise UnauthorizedError()
    if not isinstance(expires_at, int) or expires_at <= int(datetime.now(UTC).timestamp()):
        raise UnauthorizedError()
    if not isinstance(csrf_token, str) or not csrf_token:
        raise UnauthorizedError()
    if (
        not isinstance(capabilities, list)
        or not capabilities
        or not all(isinstance(item, str) for item in capabilities)
        or not set(capabilities).issubset(ALL_CAPABILITIES)
    ):
        raise UnauthorizedError()

    expected_csrf = _csrf_token(app_settings.AUTH_SESSION_SECRET or "", actor_id, expires_at)
    if not _compare_sensitive_text(csrf_token, expected_csrf):
        raise UnauthorizedError()

    return CurrentActor(
        actor_id=actor_id,
        actor_type=LOCAL_ACTOR_TYPE,
        capabilities=frozenset(capabilities),
        csrf_token=csrf_token,
        auth_mode="session",
    )


def get_current_actor(request: Request) -> CurrentActor:
    return resolve_current_actor(request)
