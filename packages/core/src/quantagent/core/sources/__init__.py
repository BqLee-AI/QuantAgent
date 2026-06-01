from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quantagent.core.sources.protocols import PullSourcePlugin, RuntimeContext, SourceBindingConfig

if TYPE_CHECKING:
    from quantagent.core.sources.service import SourceFetchResult, SourceFetchService

__all__ = [
    "PullSourcePlugin",
    "RuntimeContext",
    "SourceBindingConfig",
    "SourceFetchResult",
    "SourceFetchService",
]


def __getattr__(name: str) -> Any:
    if name in {"SourceFetchResult", "SourceFetchService"}:
        from quantagent.core.sources.service import SourceFetchResult, SourceFetchService

        return {
            "SourceFetchResult": SourceFetchResult,
            "SourceFetchService": SourceFetchService,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
