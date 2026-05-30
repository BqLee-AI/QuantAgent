from contextlib import asynccontextmanager

from fastapi import FastAPI

from quantagent.api import __version__
from quantagent.api.config.settings import Settings, settings
from quantagent.api.db import initialize_database, shutdown_database
from quantagent.api.http.exceptions import register_exception_handlers
from quantagent.api.http.middleware import RequestIdMiddleware
from quantagent.api.routers.v1 import register_api_v1_routes
from quantagent.core.events import EventBusSettings, build_event_bus_runtime


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """构建 FastAPI 应用，并注册公共中间件、异常处理和路由。"""
    current_settings = app_settings or settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 将数据库初始化放在生命周期里，避免测试或脚本在创建应用时就提前建立连接。
        event_bus_runtime = None
        try:
            initialize_database(app, current_settings)
            event_bus_runtime = build_event_bus_runtime(EventBusSettings.from_settings(current_settings))
            app.state.event_bus_runtime = event_bus_runtime
            yield
        finally:
            try:
                if event_bus_runtime is not None:
                    # Event bus 关闭失败也不能阻断数据库清理，避免 API 生命周期留下悬挂资源。
                    await event_bus_runtime.close()
            finally:
                app.state.event_bus_runtime = None
                shutdown_database(app)

    app = FastAPI(title="QuantAgent API", version=__version__, lifespan=lifespan)
    app.state.settings = current_settings
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    register_api_v1_routes(app, current_settings)
    return app


app = create_app()


def _should_enable_reload(current_settings: Settings) -> bool:
    """本地开发入口默认启用热更新，非本地环境保持单进程启动。"""
    return current_settings.APP_ENV.lower() in {"development", "local"}


def run() -> None:
    """使用配置中的主机和端口启动开发服务器。"""
    import uvicorn

    uvicorn.run(
        "quantagent.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=_should_enable_reload(settings),
    )
