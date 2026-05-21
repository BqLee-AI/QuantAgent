from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from quantagent.api.auth import (
    ALL_CAPABILITIES,
    LOCAL_ACTOR_TYPE,
    LOCAL_ADMIN_ACTOR_ID,
    CurrentActor,
    authenticate_admin_password,
    clear_session_cookie,
    development_bypass_actor,
    get_current_actor,
    issue_session,
    refresh_session,
    require_csrf,
    set_session_cookie,
)
from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.auth import AuthenticatedActorResponse, LoginRequest, LogoutResponse


public_router = APIRouter(tags=["auth"])
protected_router = APIRouter(tags=["auth"])


def _actor_response(actor: CurrentActor) -> AuthenticatedActorResponse:
    """把内部 actor 快照转换成对外 DTO，避免响应中混入 session 原文。"""
    return AuthenticatedActorResponse(
        actor_id=actor.actor_id,
        actor_type=actor.actor_type,
        capabilities=sorted(actor.capabilities),
        csrf_token=actor.csrf_token,
    )


@public_router.post("/auth/login", response_model=ApiResponse[AuthenticatedActorResponse])
def login(payload: LoginRequest, response: Response, request: Request) -> ApiResponse[AuthenticatedActorResponse]:
    app_settings = request.app.state.settings

    # development bypass 下不签发会被忽略的 session，直接返回与 /me 一致的 actor。
    if not app_settings.AUTH_ENABLED:
        clear_session_cookie(response, app_settings)
        return ApiResponse.success(_actor_response(development_bypass_actor()))

    authenticate_admin_password(payload.password, app_settings)
    session_value, csrf_token = issue_session(LOCAL_ADMIN_ACTOR_ID, app_settings)
    set_session_cookie(response, session_value, app_settings)
    return ApiResponse.success(
        AuthenticatedActorResponse(
            actor_id=LOCAL_ADMIN_ACTOR_ID,
            actor_type=LOCAL_ACTOR_TYPE,
            capabilities=sorted(ALL_CAPABILITIES),
            csrf_token=csrf_token,
        )
    )


@protected_router.post("/auth/logout", response_model=ApiResponse[LogoutResponse])
def logout(
    response: Response,
    request: Request,
    _actor: CurrentActor = Depends(require_csrf),
) -> ApiResponse[LogoutResponse]:
    # logout 也走 CSRF guard；成功后只清 cookie，不在响应体返回 session/cookie。
    clear_session_cookie(response, request.app.state.settings)
    return ApiResponse.success(LogoutResponse(cleared=True))


@protected_router.get("/me", response_model=ApiResponse[AuthenticatedActorResponse])
def me(
    response: Response,
    request: Request,
    actor: CurrentActor = Depends(get_current_actor),
) -> ApiResponse[AuthenticatedActorResponse]:
    app_settings = request.app.state.settings

    if actor.auth_mode == "session":
        session_value, csrf_token = refresh_session(actor, app_settings)
        set_session_cookie(response, session_value, app_settings)
        actor = CurrentActor(
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            capabilities=actor.capabilities,
            csrf_token=csrf_token,
            auth_mode=actor.auth_mode,
        )

    return ApiResponse.success(_actor_response(actor))

