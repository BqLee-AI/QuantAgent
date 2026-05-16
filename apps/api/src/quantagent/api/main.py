from contextlib import asynccontextmanager

from fastapi import FastAPI

from quantagent.api.exceptions import register_exception_handlers
from quantagent.api.config.settings import Settings, settings
from quantagent.api.db import initialize_database, shutdown_database
from quantagent.api.middleware import RequestIdMiddleware
from quantagent.api.routers.debug import router as debug_router
from quantagent.api.routers.health import router as health_router


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """构建 FastAPI 应用，并注册公共中间件、异常处理和路由。"""
    current_settings = app_settings or settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 将数据库初始化放在生命周期里，避免测试或脚本在创建应用时就提前建立连接。
        try:
            initialize_database(app, current_settings)
            yield
        finally:
            shutdown_database(app)

    app = FastAPI(title="QuantAgent API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router, prefix=current_settings.API_V1_PREFIX)
    if not current_settings.is_production:
        app.include_router(debug_router, prefix=current_settings.API_V1_PREFIX)
    return app


app = create_app()


def run() -> None:
    """使用配置中的主机和端口启动开发服务器。"""
    import uvicorn

    uvicorn.run("quantagent.api.main:app", host=settings.HOST, port=settings.PORT)
