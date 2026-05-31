"""Shared core infrastructure for QuantAgent."""

from quantagent.core.events import (
    DEFAULT_EVENT_SCHEMA_VERSION,
    DEFAULT_EVENT_TOPICS,
    EventBusCodec,
    EventBusConsumer,
    EventBusError,
    EventBusHandler,
    EventBusPublisher,
    EventBusSettings,
    EventEnvelope,
    EventTopicPolicy,
    InMemoryEventBus,
    KafkaEventBusConsumer,
    KafkaEventBusPublisher,
)

__all__ = [
    "__version__",
    "DEFAULT_EVENT_SCHEMA_VERSION",
    "DEFAULT_EVENT_TOPICS",
    "EventBusCodec",
    "EventBusConsumer",
    "EventBusError",
    "EventBusHandler",
    "EventBusPublisher",
    "EventBusSettings",
    "EventEnvelope",
    "EventTopicPolicy",
    "InMemoryEventBus",
    "KafkaEventBusConsumer",
    "KafkaEventBusPublisher",
]

__version__ = "0.1.0"
