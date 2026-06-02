from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quantagent.core.registry.service import PluginRegistry
from quantagent.core.runtime.service import PluginRuntimeService
from quantagent.core.worker_routing.models import (
    AnalysisRequestItem,
    CapturedSourceEventInput,
    EnrichmentStatus,
)
from quantagent.plugin_sdk import PluginRuntimeError, SourceFetchResult


@dataclass(frozen=True)
class WorkerArticleEnrichmentService:
    registry: PluginRegistry
    runtime: PluginRuntimeService

    async def build_analysis_items(
        self,
        *,
        owner_id: str,
        event: CapturedSourceEventInput,
    ) -> tuple[AnalysisRequestItem, ...]:
        items = event.payload.get("items")
        if not isinstance(items, tuple | list):
            return ()

        result_items: list[AnalysisRequestItem] = []
        for index, raw_item in enumerate(items):
            if not isinstance(raw_item, Mapping):
                continue
            result_items.append(
                await self._enrich_item(
                    owner_id=owner_id,
                    event=event,
                    raw_item=dict(raw_item),
                    item_index=index,
                )
            )
        return tuple(result_items)

    async def _enrich_item(
        self,
        *,
        owner_id: str,
        event: CapturedSourceEventInput,
        raw_item: dict[str, Any],
        item_index: int,
    ) -> AnalysisRequestItem:
        url = _optional_string(raw_item.get("url"))
        title = _optional_string(raw_item.get("title"))
        summary = _optional_string(raw_item.get("content"))
        metadata = raw_item.get("metadata")
        if not isinstance(metadata, Mapping):
            metadata = {}
        else:
            metadata = dict(metadata)

        if not self._needs_enrichment(url=url, content=summary):
            return AnalysisRequestItem(
                url=url,
                title=title,
                summary_or_content=summary,
                enrichment_status=EnrichmentStatus.NOT_NEEDED,
                source_metadata={
                    **metadata,
                    "owner_id": owner_id,
                },
            )

        readability_record = self.registry.get_plugin("quantagent.official.source.readability")
        if readability_record is None:
            return AnalysisRequestItem(
                url=url,
                title=title,
                summary_or_content=summary,
                enrichment_status=EnrichmentStatus.FAILED_DEGRADED,
                source_metadata={
                    **metadata,
                    "owner_id": owner_id,
                    "content_enrichment_failed": True,
                },
                enrichment_error_code="READABILITY_PLUGIN_NOT_REGISTERED",
            )

        invocation = await self.runtime.invoke(
            readability_record,
            capability="source.fetch",
            request_id=f"{event.request_id or event.message_id}:readability:{item_index}",
            config={"min_text_length": 400},
            input={"url": url},
            metadata={
                "binding_id": event.binding_id or "",
                "owner_id": owner_id,
                "source_message_id": event.message_id,
            },
        )
        if invocation.error is not None or invocation.result is None:
            error_code = invocation.error.code if invocation.error is not None else "READABILITY_RESULT_MISSING"
            return AnalysisRequestItem(
                url=url,
                title=title,
                summary_or_content=summary,
                enrichment_status=EnrichmentStatus.FAILED_DEGRADED,
                source_metadata={
                    **metadata,
                    "owner_id": owner_id,
                    "content_enrichment_failed": True,
                },
                enrichment_error_code=error_code,
            )

        try:
            fetch_result = SourceFetchResult.from_mapping(invocation.result.output, stage="publish")
        except PluginRuntimeError as exc:
            return AnalysisRequestItem(
                url=url,
                title=title,
                summary_or_content=summary,
                enrichment_status=EnrichmentStatus.FAILED_DEGRADED,
                source_metadata={
                    **metadata,
                    "owner_id": owner_id,
                    "content_enrichment_failed": True,
                },
                enrichment_error_code=exc.code,
            )

        if not fetch_result.items:
            return AnalysisRequestItem(
                url=url,
                title=title,
                summary_or_content=summary,
                enrichment_status=EnrichmentStatus.FAILED_DEGRADED,
                source_metadata={
                    **metadata,
                    "owner_id": owner_id,
                    "content_enrichment_failed": True,
                },
                enrichment_error_code="READABILITY_EMPTY_RESULT",
            )

        enriched_item = fetch_result.items[0]
        enriched_content = enriched_item.content or summary
        enriched_title = enriched_item.title or title
        return AnalysisRequestItem(
            url=enriched_item.url or url,
            title=enriched_title,
            summary_or_content=enriched_content,
            enrichment_status=EnrichmentStatus.SUCCEEDED,
            source_metadata={
                **metadata,
                "owner_id": owner_id,
                "reader_plugin_id": "quantagent.official.source.readability",
                "canonical_url": enriched_item.metadata.get("canonical_url"),
            },
        )

    @staticmethod
    def _needs_enrichment(*, url: str | None, content: str | None) -> bool:
        if url is None:
            return False
        if content is None:
            return True
        return len(content.strip()) < 280


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
