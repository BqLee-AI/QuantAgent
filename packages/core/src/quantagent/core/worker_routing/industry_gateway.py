from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from quantagent.plugin_sdk.io import JsonObject

from quantagent.core.worker_routing.models import CapturedSourceEventInput, IndustryEntrypointRef, IndustryGatewayResult


class IndustryGateway(Protocol):
    async def invoke(
        self,
        *,
        target: IndustryEntrypointRef,
        event: CapturedSourceEventInput,
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
    ) -> IndustryGatewayResult:
        return IndustryGatewayResult(
            status="failed",
            reason_code=self.reason_code,
            target_ref=_target_ref(target),
            attempted_at=datetime.now(UTC).isoformat(),
            error_summary=self.error_summary or {"message": "gateway failed"},
        )


def _target_ref(target: IndustryEntrypointRef) -> str:
    return f"{target.owner_type}:{target.owner_id}"
