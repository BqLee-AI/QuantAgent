from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from quantagent.core.events.dto import RawEventDraft


@dataclass(frozen=True)
class RuntimeContext:
    plugin_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceBindingConfig:
    id: str
    source_plugin_id: str
    owner_type: str
    owner_id: str
    effective_config: dict[str, Any]
    schedule_policy: dict[str, Any] = field(default_factory=dict)
    retry_policy: dict[str, Any] = field(default_factory=dict)
    rate_limit_policy: dict[str, Any] = field(default_factory=dict)
    status: str = "enabled"


class PullSourcePlugin(Protocol):
    id: str

    def load(self, context: RuntimeContext) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def reload(self, config: dict[str, Any]) -> None: ...

    def health_check(self) -> dict[str, Any]: ...

    def fetch(self, cursor: str | None, config: dict[str, Any]) -> list[RawEventDraft]: ...

