from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from quantagent.core.sources.dto import SourceOutput


class PullSourcePlugin(Protocol):
    def fetch(self, cursor: str | None, config: Mapping[str, Any]) -> list[SourceOutput]: ...
