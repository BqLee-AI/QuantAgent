from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quantagent.agent.streaming.events import AgentRunEvent, AgentRunEventType


class EventSequencer:
    def __init__(self) -> None:
        self._seq = 0

    def next(
        self,
        *,
        agent_run_id: str,
        trace_id: str,
        event_type: AgentRunEventType,
        payload: Mapping[str, Any] | None = None,
        safe_summary: str | None = None,
    ) -> AgentRunEvent:
        self._seq += 1
        return AgentRunEvent(
            agent_run_id=agent_run_id,
            trace_id=trace_id,
            type=event_type,
            seq=self._seq,
            payload=dict(payload or {}),
            safe_summary=safe_summary,
        )


def chunk_to_safe_summary(chunk: object) -> str:
    """DeepAgents chunk 格式会随版本变化；MVP 只把未知 chunk 压缩成安全摘要。"""

    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, Mapping):
        for key in ("content", "text", "message"):
            value = chunk.get(key)
            if isinstance(value, str):
                return value
        return f"deepagents chunk keys: {', '.join(str(key) for key in chunk.keys())}"
    return type(chunk).__name__
