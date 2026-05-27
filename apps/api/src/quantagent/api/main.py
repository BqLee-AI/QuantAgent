from contextlib import asynccontextmanager

from fastapi import FastAPI

from quantagent.api import __version__
from quantagent.api.config.settings import Settings, settings
from quantagent.api.db import initialize_database, shutdown_database
from quantagent.api.http.exceptions import register_exception_handlers
from quantagent.api.http.middleware import RequestIdMiddleware
from quantagent.api.routers.v1 import register_api_v1_routes


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

    app = FastAPI(title="QuantAgent API", version=__version__, lifespan=lifespan)
    app.state.settings = current_settings
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    register_api_v1_routes(app, current_settings)
    return app


app = create_app()


def run() -> None:
    """使用配置中的主机和端口启动开发服务器。"""
    import uvicorn

    uvicorn.run("quantagent.api.main:app", host=settings.API_HOST, port=settings.API_PORT)
