from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute

from quantagent.api.auth import get_current_actor
from quantagent.api.config.settings import Settings
from quantagent.api.routers.v1.auth import protected_router as auth_protected_router
from quantagent.api.routers.v1.auth import public_router as auth_public_router
from quantagent.api.routers.v1.health import router as health_router
from quantagent.api.routers.v1.version import router as version_router


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
    ApiV1RouterRegistration(router=auth_protected_router, access="protected"),
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
        from quantagent.api.routers.v1.debug import router as debug_router

        register_api_v1_protected_router(app, app_settings, debug_router)

