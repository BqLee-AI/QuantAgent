from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from quantagent.core.events.errors import EventBusError


DEFAULT_EVENT_TOPICS: Final[tuple[str, ...]] = (
    "source.event.captured",
    "event.routed",
    "industry.analysis.requested",
    "industry.analysis.completed",
    "analysis.scored",
    "decision.created",
    "approval.requested",
    "approval.completed",
    "notification.requested",
    "notification.completed",
    "broker.dry_run_requested",
    "broker.dry_run_completed",
    "runtime.failed",
)

DEFAULT_EVENT_SCHEMA_VERSION: Final[int] = 1


class EventTopicPolicy:
    def __init__(self, topics: Iterable[str] | None = None) -> None:
        self._topics = frozenset(topics or DEFAULT_EVENT_TOPICS)

    @property
    def topics(self) -> frozenset[str]:
        return self._topics

    def validate(self, topic: str) -> str:
        if not isinstance(topic, str) or not topic.strip():
            raise EventBusError(
                code="EVENT_TOPIC_INVALID",
                message="Event topic must be a non-empty string.",
                stage="topic_validation",
            )
        if topic not in self._topics:
            raise EventBusError(
                code="EVENT_TOPIC_UNREGISTERED",
                message="Event topic is not registered by the current policy.",
                stage="topic_validation",
                details={"topic": topic},
            )
        return topic
