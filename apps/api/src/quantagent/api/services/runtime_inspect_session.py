from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_optional_db_session(request: Request) -> Iterator[Session | None]:
    """Runtime inspect 允许局部 unavailable，数据库缺失时返回 None 而不是直接阻断请求。"""
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if session_factory is None:
        yield None
        return

    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
