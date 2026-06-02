from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from quantagent.core.worker_routing.analysis_request_publisher import IndustryAnalysisRequestedPublisher
from quantagent.plugin_sdk.io import JsonObject

from quantagent.core.worker_routing.models import (
    AnalysisRequestPayload,
    CapturedSourceEventInput,
    IndustryEntrypointRef,
    IndustryGatewayResult,
)


class IndustryGateway(Protocol):
    async def invoke(
        self,
        *,
        target: IndustryEntrypointRef,
        event: CapturedSourceEventInput,
        analysis_request: AnalysisRequestPayload | None = None,
    ) -> IndustryGatewayResult: ...


@dataclass
class NoopIndustryGateway:
    status: str = "accepted"
    reason_code: str | None = None

    async def invoke(
        self,
        *,
        target: IndustryEntrypointRef,
        event: CapturedSourceEventInput,
        analysis_request: AnalysisRequestPayload | None = None,
    ) -> IndustryGatewayResult:
        # V1 先固定 core port，避免 worker 直接 import 行业插件；真实行业处理链路后续再接入这个 seam。
        return IndustryGatewayResult(
            status=self.status,
            reason_code=self.reason_code,
            target_ref=_target_ref(target),
            attempted_at=datetime.now(UTC).isoformat(),
            error_summary={},
        )


@dataclass
class FailingIndustryGateway:
    reason_code: str = "INDUSTRY_ENTRYPOINT_FAILED"
    error_summary: JsonObject | None = None

    async def invoke(
        self,
        *,
        target: IndustryEntrypointRef,
        event: CapturedSourceEventInput,
        analysis_request: AnalysisRequestPayload | None = None,
    ) -> IndustryGatewayResult:
        return IndustryGatewayResult(
            status="failed",
            reason_code=self.reason_code,
            target_ref=_target_ref(target),
            attempted_at=datetime.now(UTC).isoformat(),
            error_summary=self.error_summary or {"message": "gateway failed"},
        )


@dataclass
class TopicPublishingIndustryGateway:
    publisher: IndustryAnalysisRequestedPublisher

    async def invoke(
        self,
        *,
        target: IndustryEntrypointRef,
        event: CapturedSourceEventInput,
        analysis_request: AnalysisRequestPayload | None = None,
    ) -> IndustryGatewayResult:
        if analysis_request is None:
            return IndustryGatewayResult(
                status="failed",
                reason_code="INDUSTRY_ANALYSIS_REQUEST_MISSING",
                target_ref=_target_ref(target),
                attempted_at=datetime.now(UTC).isoformat(),
                error_summary={"message": "analysis request payload is required"},
            )
        publish_result = await self.publisher.publish(analysis_request)
        return IndustryGatewayResult(
            status="accepted",
            reason_code="INDUSTRY_ANALYSIS_REQUESTED_PUBLISHED",
            target_ref=_target_ref(target),
            attempted_at=datetime.now(UTC).isoformat(),
            error_summary={
                "topic": publish_result.topic,
                "published": publish_result.published,
                "degraded": publish_result.degraded,
                "item_count": publish_result.item_count,
            },
        )


def _target_ref(target: IndustryEntrypointRef) -> str:
    return f"{target.owner_type}:{target.owner_id}"
