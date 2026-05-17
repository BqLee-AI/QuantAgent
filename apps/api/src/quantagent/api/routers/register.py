from fastapi import FastAPI

from quantagent.api.config.settings import Settings
from quantagent.api.routers.health import router as health_router
from quantagent.api.routers.version import router as version_router


def register_api_v1_routes(app: FastAPI, app_settings: Settings) -> None:
    """Register standard API v1 routers and environment-gated debug routes."""
    standard_routers = (health_router, version_router)
    for router in standard_routers:
        app.include_router(router, prefix=app_settings.API_V1_PREFIX)

    if not app_settings.is_production:
        from quantagent.api.routers.debug import router as debug_router

        app.include_router(debug_router, prefix=app_settings.API_V1_PREFIX)
