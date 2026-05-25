from __future__ import annotations

from typing import Any

from quantagent.core.events.dto import RawEventDraft
from quantagent.core.sources.protocols import RuntimeContext


class PlaceholderSourcePlugin:
    id = "quantagent.official.source.placeholder"

    def __init__(self) -> None:
        self._loaded = False
        self._started = False

    def load(self, context: RuntimeContext) -> None:
        if context.plugin_id != self.id:
            raise ValueError(f"runtime context plugin_id mismatch: {context.plugin_id}")
        self._loaded = True

    def start(self) -> None:
        if not self._loaded:
            raise RuntimeError("Placeholder source must be loaded before start.")
        self._started = True

    def stop(self) -> None:
        self._started = False

    def reload(self, config: dict[str, Any]) -> None:
        self._validate_config(config)

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "plugin_id": self.id, "started": self._started}

    def fetch(self, cursor: str | None, config: dict[str, Any]) -> list[RawEventDraft]:
        del cursor
        if not self._started:
            raise RuntimeError("Placeholder source must be started before fetch.")
        self._validate_config(config)
        return []

    def _validate_config(self, config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise ValueError("Placeholder source config must be an object.")


plugin = PlaceholderSourcePlugin()
