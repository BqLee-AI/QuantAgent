from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from quantagent.core.config.settings import settings


def create_sync_engine(database_url: str | None = None, **kwargs: object) -> Engine:
    return create_engine(database_url or settings.DATABASE_URL, **kwargs)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    bind = engine or create_sync_engine()
    return sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)
