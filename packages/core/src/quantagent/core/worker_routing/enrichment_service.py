from __future__ import annotations

import asyncio
import logging
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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerArticleEnrichmentService:
    registry: PluginRegistry
    runtime: PluginRuntimeService
    article_concurrency: int = 10

    async def build_analysis_items(
        self,
        *,
        owner_id: str,
        event: CapturedSourceEventInput,
    ) -> tuple[AnalysisRequestItem, ...]:
        items = event.payload.get("items")
        if not isinstance(items, tuple | list):
            return ()

        semaphore = asyncio.Semaphore(max(1, self.article_concurrency))

        async def enrich_bounded(index: int, raw_item: Mapping[str, object]) -> AnalysisRequestItem:
            # 并发边界按“文章”计数，而不是按 Kafka message；旧批量消息也不会被单篇慢网页拖住整批。
            async with semaphore:
                return await self._enrich_item(
                    owner_id=owner_id,
                    event=event,
                    raw_item=dict(raw_item),
                    item_index=index,
                )

        tasks = [
            asyncio.create_task(enrich_bounded(index, raw_item))
            for index, raw_item in enumerate(items)
            if isinstance(raw_item, Mapping)
        ]
        if not tasks:
            return ()
        result_items = await asyncio.gather(*tasks)
        logger.info(
            "Worker enrichment batch completed: message_id=%s binding_id=%s item_count=%s concurrency=%s",
            event.message_id,
            event.binding_id,
            len(result_items),
            max(1, self.article_concurrency),
            extra={
                "message_id": event.message_id,
                "binding_id": event.binding_id,
                "item_count": len(result_items),
                "article_concurrency": max(1, self.article_concurrency),
            },
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
            logger.info(
                "Worker enrichment skipped: message_id=%s binding_id=%s item_index=%s reason=not_needed title=%s",
                event.message_id,
                event.binding_id,
                item_index,
                _short_text(title),
                extra={
                    "message_id": event.message_id,
                    "binding_id": event.binding_id,
                    "item_index": item_index,
                    "enrichment_status": EnrichmentStatus.NOT_NEEDED.value,
                },
            )
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
            logger.warning(
                "Worker readability unavailable: message_id=%s binding_id=%s item_index=%s title=%s",
                event.message_id,
                event.binding_id,
                item_index,
                _short_text(title),
                extra={
                    "message_id": event.message_id,
                    "binding_id": event.binding_id,
                    "item_index": item_index,
                    "enrichment_status": EnrichmentStatus.FAILED_DEGRADED.value,
                    "enrichment_error_code": "READABILITY_PLUGIN_NOT_REGISTERED",
                },
            )
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

        logger.info(
            "Worker readability started: message_id=%s binding_id=%s item_index=%s title=%s",
            event.message_id,
            event.binding_id,
            item_index,
            _short_text(title),
            extra={
                "message_id": event.message_id,
                "binding_id": event.binding_id,
                "item_index": item_index,
                "reader_plugin_id": "quantagent.official.source.readability",
            },
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
            logger.warning(
                "Worker readability failed degraded: message_id=%s binding_id=%s item_index=%s error_code=%s title=%s",
                event.message_id,
                event.binding_id,
                item_index,
                error_code,
                _short_text(title),
                extra={
                    "message_id": event.message_id,
                    "binding_id": event.binding_id,
                    "item_index": item_index,
                    "enrichment_status": EnrichmentStatus.FAILED_DEGRADED.value,
                    "enrichment_error_code": error_code,
                },
            )
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
            logger.warning(
                "Worker readability output invalid degraded: message_id=%s binding_id=%s item_index=%s error_code=%s title=%s",
                event.message_id,
                event.binding_id,
                item_index,
                exc.code,
                _short_text(title),
                extra={
                    "message_id": event.message_id,
                    "binding_id": event.binding_id,
                    "item_index": item_index,
                    "enrichment_status": EnrichmentStatus.FAILED_DEGRADED.value,
                    "enrichment_error_code": exc.code,
                },
            )
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
            logger.warning(
                "Worker readability empty degraded: message_id=%s binding_id=%s item_index=%s title=%s",
                event.message_id,
                event.binding_id,
                item_index,
                _short_text(title),
                extra={
                    "message_id": event.message_id,
                    "binding_id": event.binding_id,
                    "item_index": item_index,
                    "enrichment_status": EnrichmentStatus.FAILED_DEGRADED.value,
                    "enrichment_error_code": "READABILITY_EMPTY_RESULT",
                },
            )
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
        logger.info(
            "Worker readability succeeded: message_id=%s binding_id=%s item_index=%s content_length=%s title=%s",
            event.message_id,
            event.binding_id,
            item_index,
            len(enriched_content or ""),
            _short_text(enriched_title),
            extra={
                "message_id": event.message_id,
                "binding_id": event.binding_id,
                "item_index": item_index,
                "enrichment_status": EnrichmentStatus.SUCCEEDED.value,
                "content_length": len(enriched_content or ""),
            },
        )
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


def _short_text(value: str | None, *, limit: int = 120) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."
