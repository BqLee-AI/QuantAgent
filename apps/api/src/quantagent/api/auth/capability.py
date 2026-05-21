from __future__ import annotations

from fastapi import Depends

from quantagent.api.auth.actor import ALL_CAPABILITIES, CurrentActor
from quantagent.api.auth.session import get_current_actor
from quantagent.api.http.errors import ForbiddenError


def require_capability(capability: str):
    """生成 FastAPI dependency，用集中 capability 集合保护后续业务 route。"""
    if capability not in ALL_CAPABILITIES:
        raise ValueError(f"Unknown capability: {capability}")

    def dependency(actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
        if capability not in actor.capabilities:
            raise ForbiddenError()
        return actor

    return dependency

