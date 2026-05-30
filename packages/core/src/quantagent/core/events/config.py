from __future__ import annotations

from dataclasses import dataclass

from quantagent.core.config.settings import Settings
from quantagent.core.events.errors import EventBusError


@dataclass(frozen=True)
class EventBusSettings:
    backend: str
    kafka_bootstrap_servers: str | None
    kafka_client_id: str
    kafka_default_group_id: str
    topic_prefix: str

    @classmethod
    def from_settings(cls, app_settings: Settings) -> EventBusSettings:
        resolved = cls(
            backend=app_settings.EVENT_BUS_BACKEND,
            kafka_bootstrap_servers=app_settings.EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS,
            kafka_client_id=app_settings.EVENT_BUS_KAFKA_CLIENT_ID,
            kafka_default_group_id=app_settings.EVENT_BUS_KAFKA_DEFAULT_GROUP_ID,
            topic_prefix=app_settings.EVENT_BUS_TOPIC_PREFIX,
        )
        resolved.validate()
        return resolved

    def validate(self) -> None:
        if self.backend not in {"memory", "kafka"}:
            raise EventBusError(
                code="EVENT_BUS_BACKEND_INVALID",
                message="Event bus backend must be either 'memory' or 'kafka'.",
                stage="config",
                details={"backend": self.backend},
            )
        bootstrap_servers = (self.kafka_bootstrap_servers or "").strip()
        if self.backend == "kafka" and not bootstrap_servers:
            raise EventBusError(
                code="EVENT_BUS_KAFKA_CONFIG_MISSING",
                message="Kafka backend requires bootstrap servers.",
                stage="config",
            )
