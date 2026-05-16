from __future__ import annotations

from collections.abc import Iterator
import logging

from fastapi import FastAPI, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from quantagent.api.config.settings import Settings
from quantagent.api.errors import ServiceUnavailableError
from quantagent.core.db.session import create_session_factory, create_sync_engine


DB_ENGINE_STATE_KEY = "db_engine"
DB_SESSION_FACTORY_STATE_KEY = "db_session_factory"
logger = logging.getLogger("quantagent.api")


def initialize_database(app: FastAPI, app_settings: Settings) -> None:
    app.state.db_engine = None
    app.state.db_session_factory = None
    if not app_settings.DATABASE_URL:
        return

    engine = create_sync_engine(app_settings.DATABASE_URL)
    app.state.db_engine = engine
    app.state.db_session_factory = create_session_factory(engine)


def shutdown_database(app: FastAPI) -> None:
    engine = getattr(app.state, DB_ENGINE_STATE_KEY, None)
    app.state.db_session_factory = None
    app.state.db_engine = None
    if isinstance(engine, Engine):
        engine.dispose()


def get_db_session(request: Request) -> Iterator[Session]:
    session_factory = getattr(request.app.state, DB_SESSION_FACTORY_STATE_KEY, None)
    if session_factory is None:
        raise ServiceUnavailableError("Database not configured")

    try:
        session = session_factory()
    except Exception as exc:
        logger.warning("Database session creation failed: %s", exc.__class__.__name__)
        raise ServiceUnavailableError("Database not ready") from exc

    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
