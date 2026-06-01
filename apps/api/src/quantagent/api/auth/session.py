from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import uuid

from fastapi import Request, Response

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
from quantagent.api.observability import events
from quantagent.api.observability.context import set_actor_context
from quantagent.api.observability.logging import log_security_event


SESSION_V1 = 1
SESSION_V2 = 2


@dataclass(frozen=True)
class SessionData:
    version: int
    session_id: str
    subject: str
    actor_type: str
    issued_at: int
    expires_at: int
    max_expires_at: int
    capabilities: frozenset[str]
    csrf_token: str


@dataclass(frozen=True)
class IssuedSession:
    value: str
    data: SessionData


@dataclass(frozen=True)
class AuthState:
    actor: CurrentActor
    session: SessionData | None


def _now_timestamp() -> int:
    return int(datetime.now(UTC).timestamp())


def _hmac_sha256(secret: str, value: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _session_signature(secret: str, payload_json: str) -> str:
    """对规范化后的 session payload 签名，避免客户端篡改 cookie 内容。"""
    return _hmac_sha256(secret, payload_json)


def _csrf_token_for_v1(secret: str, actor_id: str, expires_at: int) -> str:
    if not secret:
        raise ValueError("session secret must not be empty")
    return _hmac_sha256(secret, f"csrf:{actor_id}:{expires_at}")


def _csrf_token_for_v2(secret: str, session_id: str, subject: str) -> str:
    if not secret:
        raise ValueError("session secret must not be empty")
    return _hmac_sha256(secret, f"csrf:v2:{session_id}:{subject}")


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


def _validate_string_field(value: object) -> str:
    """校验 session payload 的字符串字段，缺失或为空时按未授权处理。"""
    if not isinstance(value, str) or not value:
        raise UnauthorizedError()
    return value


def _validate_capabilities(capabilities: object) -> frozenset[str]:
    """校验 payload 中的 capabilities，要求为非空字符串列表且受集中 capability 集合约束。"""
    if (
        not isinstance(capabilities, list)
        or not capabilities
        or not all(isinstance(item, str) for item in capabilities)
    ):
        raise UnauthorizedError()
    capability_set = frozenset(capabilities)
    if not capability_set.issubset(ALL_CAPABILITIES):
        raise UnauthorizedError()
    return capability_set


def _parse_v1_session(payload: dict[str, object], secret: str) -> SessionData:
    """解析并校验 legacy v1 session payload，供兼容升级路径复用。"""
    subject = _validate_string_field(payload.get("sub"))
    actor_type = _validate_string_field(payload.get("type"))
    expires_at = payload.get("exp")
    csrf_token = _validate_string_field(payload.get("csrf"))
    capabilities = _validate_capabilities(payload.get("capabilities"))

    if not isinstance(expires_at, int) or expires_at <= _now_timestamp():
        raise UnauthorizedError()

    expected_csrf = _csrf_token_for_v1(secret, subject, expires_at)
    if not _compare_sensitive_text(csrf_token, expected_csrf):
        raise UnauthorizedError()

    return SessionData(
        version=SESSION_V1,
        session_id="",
        subject=subject,
        actor_type=actor_type,
        issued_at=0,
        expires_at=expires_at,
        max_expires_at=expires_at,
        capabilities=capabilities,
        csrf_token=csrf_token,
    )


def _parse_v2_session(payload: dict[str, object], secret: str) -> SessionData:
    """解析并校验 v2 session payload，并派生绑定稳定 session identity 的 CSRF token。"""
    session_id = _validate_string_field(payload.get("sid"))
    subject = _validate_string_field(payload.get("sub"))
    actor_type = _validate_string_field(payload.get("actor_type"))
    issued_at = payload.get("iat")
    expires_at = payload.get("exp")
    max_expires_at = payload.get("max_exp")
    capabilities = _validate_capabilities(payload.get("capabilities"))

    now_timestamp = _now_timestamp()
    if not all(isinstance(value, int) for value in (issued_at, expires_at, max_expires_at)):
        raise UnauthorizedError()
    if issued_at > expires_at or expires_at > max_expires_at:
        raise UnauthorizedError()
    if expires_at <= now_timestamp or max_expires_at <= now_timestamp:
        raise UnauthorizedError()

    csrf_token = _csrf_token_for_v2(secret, session_id, subject)
    return SessionData(
        version=SESSION_V2,
        session_id=session_id,
        subject=subject,
        actor_type=actor_type,
        issued_at=issued_at,
        expires_at=expires_at,
        max_expires_at=max_expires_at,
        capabilities=capabilities,
        csrf_token=csrf_token,
    )


def _parse_session(payload: dict[str, object], secret: str) -> SessionData:
    """按 payload version 分发到 v1/v2 解析逻辑，形成统一的 SessionData。"""
    version = payload.get("v")
    if version in (None, SESSION_V1):
        return _parse_v1_session(payload, secret)
    if version == SESSION_V2:
        return _parse_v2_session(payload, secret)
    raise UnauthorizedError()


def _current_actor_from_session(session: SessionData) -> CurrentActor:
    """把已校验的 session 数据映射为当前实现支持的 CurrentActor。"""
    if session.subject != LOCAL_ADMIN_ACTOR_ID or session.actor_type != LOCAL_ACTOR_TYPE:
        raise UnauthorizedError()

    return CurrentActor(
        actor_id=session.subject,
        actor_type=LOCAL_ACTOR_TYPE,
        capabilities=session.capabilities,
        csrf_token=session.csrf_token,
        auth_mode="session",
    )


def issue_session(
    actor_id: str,
    app_settings: Settings,
    *,
    capabilities: frozenset[str] | None = None,
    actor_type: str = LOCAL_ACTOR_TYPE,
    issued_at: int | None = None,
    expires_at: int | None = None,
    max_expires_at: int | None = None,
    session_id: str | None = None,
) -> IssuedSession:
    """签发本地单用户 session，并返回给前端 bootstrap 用的 CSRF token。"""
    if actor_id != LOCAL_ADMIN_ACTOR_ID:
        raise ValueError(f"Unsupported actor_id for session issuance: {actor_id}")

    capability_set = ALL_CAPABILITIES if capabilities is None else capabilities
    if not capability_set or not capability_set.issubset(ALL_CAPABILITIES):
        raise ValueError("capabilities must be a non-empty subset of ALL_CAPABILITIES")

    issued_timestamp = issued_at if issued_at is not None else _now_timestamp()
    max_expiration = max_expires_at if max_expires_at is not None else int(
        (datetime.fromtimestamp(issued_timestamp, UTC) + timedelta(seconds=app_settings.AUTH_SESSION_ABSOLUTE_LIFETIME_SECONDS)).timestamp()
    )
    session_expiration = expires_at if expires_at is not None else min(
        int((datetime.fromtimestamp(issued_timestamp, UTC) + timedelta(seconds=app_settings.AUTH_SESSION_LIFETIME_SECONDS)).timestamp()),
        max_expiration,
    )
    if session_expiration > max_expiration:
        raise ValueError("expires_at must not exceed max_expires_at")

    resolved_session_id = session_id or uuid.uuid4().hex
    csrf_token = _csrf_token_for_v2(app_settings.AUTH_SESSION_SECRET or "", resolved_session_id, actor_id)
    session = SessionData(
        version=SESSION_V2,
        session_id=resolved_session_id,
        subject=actor_id,
        actor_type=actor_type,
        issued_at=issued_timestamp,
        expires_at=session_expiration,
        max_expires_at=max_expiration,
        capabilities=capability_set,
        csrf_token=csrf_token,
    )
    payload = {
        "v": SESSION_V2,
        "sid": session.session_id,
        "sub": session.subject,
        "actor_type": session.actor_type,
        "iat": session.issued_at,
        "exp": session.expires_at,
        "max_exp": session.max_expires_at,
        "capabilities": sorted(session.capabilities),
    }
    return IssuedSession(
        value=_serialize_session(payload, app_settings.AUTH_SESSION_SECRET or ""),
        data=session,
    )


def _issue_v1_session(
    actor_id: str,
    app_settings: Settings,
    *,
    capabilities: frozenset[str] | None = None,
    expires_at: int | None = None,
) -> IssuedSession:
    if actor_id != LOCAL_ADMIN_ACTOR_ID:
        raise ValueError(f"Unsupported actor_id for session issuance: {actor_id}")

    capability_set = ALL_CAPABILITIES if capabilities is None else capabilities
    if not capability_set or not capability_set.issubset(ALL_CAPABILITIES):
        raise ValueError("capabilities must be a non-empty subset of ALL_CAPABILITIES")

    session_expiration = expires_at if expires_at is not None else int(
        (datetime.now(UTC) + timedelta(seconds=app_settings.AUTH_SESSION_LIFETIME_SECONDS)).timestamp()
    )
    csrf_token = _csrf_token_for_v1(app_settings.AUTH_SESSION_SECRET or "", actor_id, session_expiration)
    payload = {
        "sub": actor_id,
        "type": LOCAL_ACTOR_TYPE,
        "exp": session_expiration,
        "csrf": csrf_token,
        "capabilities": sorted(capability_set),
    }
    return IssuedSession(
        value=_serialize_session(payload, app_settings.AUTH_SESSION_SECRET or ""),
        data=SessionData(
            version=SESSION_V1,
            session_id="",
            subject=actor_id,
            actor_type=LOCAL_ACTOR_TYPE,
            issued_at=0,
            expires_at=session_expiration,
            max_expires_at=session_expiration,
            capabilities=capability_set,
            csrf_token=csrf_token,
        ),
    )


def upgrade_v1_session(
    session: SessionData,
    app_settings: Settings,
    *,
    now_timestamp: int | None = None,
) -> IssuedSession:
    """把 legacy v1 session 升级成 v2，并固定 absolute expiration 为旧 v1 的原始过期时间。"""
    if session.version != SESSION_V1:
        raise ValueError("upgrade_v1_session only accepts v1 sessions")

    upgraded_issued_at = now_timestamp if now_timestamp is not None else _now_timestamp()
    return issue_session(
        session.subject,
        app_settings,
        capabilities=session.capabilities,
        actor_type=session.actor_type,
        issued_at=upgraded_issued_at,
        expires_at=session.expires_at,
        max_expires_at=session.max_expires_at,
        session_id=uuid.uuid4().hex,
    )


def refresh_session(
    session: SessionData,
    app_settings: Settings,
    *,
    now_timestamp: int | None = None,
) -> IssuedSession | None:
    """显式 refresh 仅在接近 idle 超时时重签 v2 session，且不会突破 absolute expiration。

    旧 v1 session 在显式 refresh 时总会升级为 v2，因此该分支总是返回新的 cookie。
    """
    if session.version == SESSION_V1:
        return upgrade_v1_session(session, app_settings, now_timestamp=now_timestamp)

    current_timestamp = now_timestamp if now_timestamp is not None else _now_timestamp()
    remaining_idle_seconds = session.expires_at - current_timestamp
    if remaining_idle_seconds > app_settings.AUTH_SESSION_REFRESH_THRESHOLD_SECONDS:
        return None

    next_expiration = min(
        current_timestamp + app_settings.AUTH_SESSION_LIFETIME_SECONDS,
        session.max_expires_at,
    )
    if next_expiration <= session.expires_at:
        return None

    return issue_session(
        session.subject,
        app_settings,
        capabilities=session.capabilities,
        actor_type=session.actor_type,
        issued_at=session.issued_at,
        expires_at=next_expiration,
        max_expires_at=session.max_expires_at,
        session_id=session.session_id,
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


def session_cookie_max_age(expires_at: int, *, now_timestamp: int | None = None) -> int:
    """返回 cookie 从当前时刻到 `expires_at` 的剩余秒数，最小为 0。"""
    return max(expires_at - (now_timestamp if now_timestamp is not None else _now_timestamp()), 0)


def set_session_cookie(
    response: Response,
    session_value: str,
    app_settings: Settings,
    *,
    max_age: int | None = None,
) -> None:
    """写入 HttpOnly session cookie，避免前端 JavaScript 读取 session 原文。"""
    response.set_cookie(
        key=app_settings.AUTH_COOKIE_NAME,
        value=session_value,
        max_age=app_settings.AUTH_SESSION_LIFETIME_SECONDS if max_age is None else max_age,
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


def resolve_auth_state(request: Request) -> AuthState:
    """统一解析当前 actor；需要 session 元数据时复用该入口，而不是自行读 cookie。"""
    app_settings: Settings = request.app.state.settings

    if not app_settings.AUTH_ENABLED:
        actor = development_bypass_actor()
        set_actor_context(actor_type=actor.actor_type, actor_id=actor.actor_id)
        return AuthState(actor=actor, session=None)

    raw_session = request.cookies.get(app_settings.AUTH_COOKIE_NAME)
    if not raw_session:
        log_security_event(request, event=events.AUTH_UNAUTHORIZED, failure_type="missing_session")
        raise UnauthorizedError()

    try:
        session = _parse_session(
            _deserialize_session(raw_session, app_settings.AUTH_SESSION_SECRET or ""),
            app_settings.AUTH_SESSION_SECRET or "",
        )
        actor = _current_actor_from_session(session)
    except UnauthorizedError:
        log_security_event(request, event=events.AUTH_UNAUTHORIZED, failure_type="invalid_session")
        raise

    set_actor_context(actor_type=actor.actor_type, actor_id=actor.actor_id)
    return AuthState(actor=actor, session=session)


def resolve_current_actor(request: Request) -> CurrentActor:
    return resolve_auth_state(request).actor


def get_current_actor(request: Request) -> CurrentActor:
    return resolve_current_actor(request)
