from fastapi import FastAPI

from quantagent_api.exceptions import register_exception_handlers
from quantagent_api.config.settings import Settings, settings
from quantagent_api.middleware import RequestIdMiddleware
from quantagent_api.routers.debug import router as debug_router
from quantagent_api.routers.health import router as health_router


def create_app(app_settings: Settings | None = None) -> FastAPI:
    current_settings = app_settings or settings
    app = FastAPI(title="QuantAgent API", version="0.1.0")
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router, prefix=current_settings.API_V1_PREFIX)
    if not current_settings.is_production:
        app.include_router(debug_router, prefix=current_settings.API_V1_PREFIX)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("quantagent_api.main:app", host=settings.HOST, port=settings.PORT)
