from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute

from quantagent.api.auth import get_current_actor
from quantagent.api.config.settings import Settings
from quantagent.api.routers.v1.auth import protected_router as auth_protected_router
from quantagent.api.routers.v1.auth import public_router as auth_public_router
from quantagent.api.routers.v1.events import router as events_router
from quantagent.api.routers.v1.notification_ingress import router as notification_ingress_router
from quantagent.api.routers.v1.health import router as health_router
from quantagent.api.routers.v1.models import router as models_router
from quantagent.api.routers.v1.plugins import router as plugins_router
from quantagent.api.routers.v1.agent_runs import router as agent_runs_router
from quantagent.api.routers.v1.approvals import router as approvals_router
from quantagent.api.routers.v1.runtime_errors import router as runtime_errors_router
from quantagent.api.routers.v1.runtime_health import router as runtime_health_router
from quantagent.api.routers.v1.runtime_audit import router as runtime_audit_router
from quantagent.api.routers.v1.raw_events import router as raw_events_router
from quantagent.api.routers.v1.scheduler_runs import router as scheduler_runs_router
from quantagent.api.routers.v1.source_bindings import router as source_bindings_router
from quantagent.api.routers.v1.tool_invocations import router as tool_invocations_router
from quantagent.api.routers.v1.version import router as version_router
from quantagent.api.routers.v1.wallet import router as wallet_router


ApiV1RouteAccess = Literal["public", "protected"]
_HTTP_METHODS = frozenset({"DELETE", "GET", "PATCH", "POST", "PUT"})


@dataclass(frozen=True)
class ApiV1RouterRegistration:
    router: APIRouter
    access: ApiV1RouteAccess


STANDARD_API_V1_ROUTER_REGISTRATIONS = (
    ApiV1RouterRegistration(router=health_router, access="public"),
    ApiV1RouterRegistration(router=version_router, access="public"),
    ApiV1RouterRegistration(router=auth_public_router, access="public"),
    ApiV1RouterRegistration(router=notification_ingress_router, access="public"),
    ApiV1RouterRegistration(router=auth_protected_router, access="protected"),
    ApiV1RouterRegistration(router=approvals_router, access="protected"),
    ApiV1RouterRegistration(router=events_router, access="protected"),
    ApiV1RouterRegistration(router=plugins_router, access="protected"),
    ApiV1RouterRegistration(router=source_bindings_router, access="protected"),
    ApiV1RouterRegistration(router=scheduler_runs_router, access="protected"),
    ApiV1RouterRegistration(router=wallet_router, access="protected"),
    ApiV1RouterRegistration(router=models_router, access="protected"),
    ApiV1RouterRegistration(router=runtime_health_router, access="protected"),
    ApiV1RouterRegistration(router=runtime_audit_router, access="protected"),
    ApiV1RouterRegistration(router=raw_events_router, access="protected"),
    ApiV1RouterRegistration(router=runtime_errors_router, access="protected"),
    ApiV1RouterRegistration(router=agent_runs_router, access="protected"),
    ApiV1RouterRegistration(router=tool_invocations_router, access="protected"),
)


def _expand_router_routes(router: APIRouter, *, prefix: str = "") -> frozenset[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or ():
            if method in _HTTP_METHODS:
                routes.add((method, f"{prefix}{route.path}"))
    return frozenset(routes)


API_V1_PUBLIC_ROUTE_ALLOWLIST = frozenset(
    route
    for registration in STANDARD_API_V1_ROUTER_REGISTRATIONS
    if registration.access == "public"
    for route in _expand_router_routes(registration.router)
)


def build_api_v1_public_route_allowlist(api_v1_prefix: str) -> frozenset[tuple[str, str]]:
    return frozenset((method, f"{api_v1_prefix}{path}") for method, path in API_V1_PUBLIC_ROUTE_ALLOWLIST)


def register_api_v1_router(
    app: FastAPI,
    app_settings: Settings,
    registration: ApiV1RouterRegistration,
) -> None:
    include_kwargs: dict[str, object] = {"prefix": app_settings.API_V1_PREFIX}
    if registration.access == "protected":
        include_kwargs["dependencies"] = [Depends(get_current_actor)]
    app.include_router(registration.router, **include_kwargs)


def register_api_v1_protected_router(app: FastAPI, app_settings: Settings, router: APIRouter) -> None:
    register_api_v1_router(
        app,
        app_settings,
        ApiV1RouterRegistration(router=router, access="protected"),
    )


def register_api_v1_routes(app: FastAPI, app_settings: Settings) -> None:
    """Register standard API v1 routers and environment-gated debug routes."""
    for registration in STANDARD_API_V1_ROUTER_REGISTRATIONS:
        register_api_v1_router(app, app_settings, registration)

    if not app_settings.is_production:
        from quantagent.api.routers.v1.agent_debug import router as agent_debug_router
        from quantagent.api.routers.v1.debug import router as debug_router

        register_api_v1_protected_router(app, app_settings, debug_router)
        register_api_v1_protected_router(app, app_settings, agent_debug_router)
