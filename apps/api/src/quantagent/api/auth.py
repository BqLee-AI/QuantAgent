from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
from typing import Literal

from fastapi import Depends, Request, Response

from quantagent.api.config.settings import Settings
from quantagent.api.errors import ForbiddenError, UnauthorizedError
from quantagent.api.middleware import get_request_id


LOCAL_ADMIN_ACTOR_ID = "local_admin"
LOCAL_DEV_ACTOR_ID = "local_dev"
LOCAL_ACTOR_TYPE = "local_single_user"
DEVELOPMENT_BYPASS_CSRF_TOKEN = "development-bypass-csrf-token"

RUNTIME_INSPECT_CAPABILITY = "runtime.inspect"
PLUGIN_CONFIGURE_CAPABILITY = "plugin.configure"
PLUGIN_INSTALL_CAPABILITY = "plugin.install"
SECRET_MANAGE_CAPABILITY = "secret.manage"
APPROVAL_APPROVE_CAPABILITY = "approval.approve"
APPROVAL_AMEND_CAPABILITY = "approval.amend"
EXECUTOR_DRY_RUN_CAPABILITY = "executor.dry_run"

ALL_CAPABILITIES = frozenset(
    {
        RUNTIME_INSPECT_CAPABILITY,
        PLUGIN_CONFIGURE_CAPABILITY,
        PLUGIN_INSTALL_CAPABILITY,
        SECRET_MANAGE_CAPABILITY,
        APPROVAL_APPROVE_CAPABILITY,
        APPROVAL_AMEND_CAPABILITY,
        EXECUTOR_DRY_RUN_CAPABILITY,
    }
)


@dataclass(frozen=True)
class CurrentActor:
    """请求处理期间传递的脱敏身份快照，不包含 session/cookie 原文。"""

    actor_id: str
    actor_type: Literal["local_single_user"]
    capabilities: frozenset[str]
    csrf_token: str
    auth_mode: Literal["session", "development_bypass"]


@dataclass(frozen=True)
class ActorAuditContext:
    """供后续高风险 handler 复用的审计上下文，只保留 actor 与请求元数据。"""

    actor_id: str
    actor_type: str
    capabilities: tuple[str, ...]
    request_id: str
    request_method: str
    request_path: str


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


def require_capability(capability: str):
    """生成 FastAPI dependency，用集中 capability 集合保护后续业务 route。"""
    if capability not in ALL_CAPABILITIES:
        raise ValueError(f"Unknown capability: {capability}")

    def dependency(actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
        if capability not in actor.capabilities:
            raise ForbiddenError()
        return actor

    return dependency


def require_csrf(request: Request, actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
    """校验 cookie-session 写操作的 CSRF header，不回显提交值或期望值。"""
    app_settings: Settings = request.app.state.settings
    submitted_token = request.headers.get(app_settings.AUTH_CSRF_HEADER_NAME)
    if not submitted_token or not _compare_sensitive_text(submitted_token, actor.csrf_token):
        raise ForbiddenError("Forbidden")
    return actor


def build_actor_audit_context(request: Request, actor: CurrentActor) -> ActorAuditContext:
    """构造脱敏审计上下文，供后续 Policy Gate 或审计持久化复用。"""
    return ActorAuditContext(
        actor_id=actor.actor_id,
        actor_type=actor.actor_type,
        capabilities=tuple(sorted(actor.capabilities)),
        request_id=get_request_id(request),
        request_method=request.method,
        request_path=request.url.path,
    )
