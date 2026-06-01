from __future__ import annotations

from collections.abc import Iterator
import logging

from fastapi import FastAPI, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from quantagent.api.config.settings import Settings
from quantagent.api.http.errors import ServiceUnavailableError
from quantagent.api.observability import events
from quantagent.api.observability.logging import log_error_event, log_structured
from quantagent.core.db.session import create_session_factory, create_sync_engine


DB_ENGINE_STATE_KEY = "db_engine"
DB_SESSION_FACTORY_STATE_KEY = "db_session_factory"
logger = logging.getLogger("quantagent.api")


def initialize_database(app: FastAPI, app_settings: Settings) -> None:
    """在存在数据库配置时，把 engine 和 session factory 挂到应用状态上。"""
    app.state.db_engine = None
    app.state.db_session_factory = None
    if not app_settings.DATABASE_URL:
        log_structured(logging.INFO, event=events.DB_INITIALIZED, stream="app", component="database", configured=False)
        return

    try:
        engine = create_sync_engine(app_settings.DATABASE_URL)
        app.state.db_engine = engine
        app.state.db_session_factory = create_session_factory(engine)
    except Exception as exc:
        log_structured(
            logging.ERROR,
            event=events.DB_INITIALIZE_FAILED,
            stream="error",
            component="database",
            failure_type="initialize",
            exception_type=exc.__class__.__name__,
        )
        raise

    log_structured(logging.INFO, event=events.DB_INITIALIZED, stream="app", component="database", configured=True)


def shutdown_database(app: FastAPI) -> None:
    """释放已配置的数据库引擎，并清理应用上的数据库状态。"""
    engine = getattr(app.state, DB_ENGINE_STATE_KEY, None)
    app.state.db_session_factory = None
    app.state.db_engine = None
    if isinstance(engine, Engine):
        engine.dispose()


def get_db_session(request: Request) -> Iterator[Session]:
    """按请求提供 SQLAlchemy Session，并且不隐式提交事务。"""
    session_factory = getattr(request.app.state, DB_SESSION_FACTORY_STATE_KEY, None)
    if session_factory is None:
        log_error_event(
            request,
            event=events.DB_SESSION_FACTORY_MISSING,
            component="database",
            failure_type="session_factory_missing",
        )
        raise ServiceUnavailableError("Database not configured")

    try:
        session = session_factory()
    except Exception as exc:
        log_error_event(
            request,
            event=events.DB_SESSION_CREATE_FAILED,
            component="database",
            failure_type="session_create",
            exception_type=exc.__class__.__name__,
        )
        logger.warning("Database session creation failed: %s", exc.__class__.__name__)
        raise ServiceUnavailableError("Database not ready") from exc

    try:
        yield session
    except Exception:
        # 下游逻辑出错时主动回滚，避免半完成的事务污染后续请求。
        session.rollback()
        raise
    finally:
        session.close()
