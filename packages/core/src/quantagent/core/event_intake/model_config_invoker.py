from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass

from quantagent.core.event_intake.context import IndustryEventContextV1
from quantagent.core.event_intake.runner import StructuredModelInvocation, StructuredModelInvoker
from quantagent.core.model_config import (
    ModelConfigService,
    ModelConfigServiceError,
    ModelPresetKey,
)


_SYSTEM_PROMPT = """You are the QuantAgent V1 event intake router.
Return exactly one JSON object that matches the requested schema_version.
Do not call tools.
Do not add markdown.
Do not add any text before or after the JSON object.
Use only evidence from the provided context.
User-readable semantic text fields must be written in Simplified Chinese by default.
Machine fields must keep the specified English enum/code values.
Do not create a display object or any UI-only Chinese text bucket.
Always include every required top-level field:
- schema_version
- decision
- discard_reason
- quality
- industry_relevance
- structured_news
- routing
- audit
The routing object must contain target_industries, target_topics, priority, requires_deep_analysis, requires_human_review, and dedupe_key_hint."""


@dataclass
class ModelConfigStructuredModelInvoker(StructuredModelInvoker):
    service: ModelConfigService | None = None
    preset_key: ModelPresetKey = ModelPresetKey.ECONOMY_TEXT
    service_factory: Callable[[], ModelConfigService] | None = None
    close_service: Callable[[ModelConfigService], None] | None = None

    async def invoke(
        self,
        *,
        context: IndustryEventContextV1,
        output_schema: str,
    ) -> StructuredModelInvocation:
        request_id = context.trace.request_id
        trace_id = context.trace.correlation_id or context.trace.request_id
        user_prompt = _build_user_prompt(context=context, output_schema=output_schema)
        call_result, invocation = await asyncio.to_thread(
            self._invoke_in_thread,
            user_prompt=user_prompt,
            output_schema=output_schema,
            request_id=request_id,
            trace_id=trace_id,
        )
        normalized_output = dict(call_result.output)
        normalized_output.setdefault("schema_version", output_schema)
        return StructuredModelInvocation(
            output=normalized_output,
            metadata={
                "status": "configured_provider",
                "provider_id": invocation.provider_id,
                "provider_name": invocation.provider_name,
                "model": invocation.model,
                "preset_key": invocation.preset_key.value if invocation.preset_key else None,
                "invocation_id": invocation.id,
                "token_usage": {
                    "prompt_tokens": invocation.token_usage.prompt_tokens,
                    "completion_tokens": invocation.token_usage.completion_tokens,
                    "total_tokens": invocation.token_usage.total_tokens,
                },
            },
        )

    def _invoke_in_thread(
        self,
        *,
        user_prompt: str,
        output_schema: str,
        request_id: str | None,
        trace_id: str | None,
    ):
        if self.service_factory is None:
            if self.service is None:
                raise ModelConfigServiceError(
                    "ModelConfigStructuredModelInvoker requires service or service_factory",
                    code="MODEL_INVOKER_SERVICE_MISSING",
                )
            # 兼容旧单元测试和同步调用方；生产 worker 使用 service_factory，避免 Session 跨线程迁移。
            return self.service.invoke_structured_json(
                preset_key=self.preset_key,
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                request_id=request_id,
                trace_id=trace_id,
            )

        service = self.service_factory()
        try:
            return service.invoke_structured_json(
                preset_key=self.preset_key,
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                request_id=request_id,
                trace_id=trace_id,
            )
        finally:
            if self.close_service is not None:
                self.close_service(service)


def _build_user_prompt(*, context: IndustryEventContextV1, output_schema: str) -> str:
    context_json = json.loads(json.dumps(context.to_mapping(), ensure_ascii=True, default=_json_default))
    return "\n".join(
        [
            f"schema_version={output_schema}",
            "task=Decide whether to discard, route, or review this article for semiconductor industry intake.",
            "rules:",
            "- Use one decision only: discard, route, or review.",
            "- If route, include at least one target_industries entry.",
            "- If discard, use a concrete discard_reason, not not_discarded.",
            "- If review, set requires_human_review true or keep confidence below review threshold.",
            "- Preserve enrichment_status and content_completeness semantics from context.",
            "- Write user-readable semantic fields in Simplified Chinese: structured_news.canonical_title, structured_news.short_summary, bullet_summary, tag labels, event_type_label, quality.reason_summary, industry_relevance.reason_summary, routing.reason_summary, routing.next_step_hint, audit.reason_summary.",
            "- Keep machine fields in English enum/code form: decision, discard_reason, relationship, priority, schema_version, industry_id, ticker, URL, numeric values, and evidence refs.",
            "- Do not output display, display.headline, display.summary_markdown, display.badges, or any UI-only text bucket.",
            "- Keep output compact and factual.",
            "required_output_shape_example:",
            json.dumps(
                {
                    "schema_version": output_schema,
                    "decision": "route",
                    "discard_reason": "not_discarded",
                    "quality": {
                        "is_spam": False,
                        "noise_flags": [],
                        "content_completeness": "full",
                        "enrichment_status": "succeeded",
                        "confidence": 0.82,
                        "reason_summary": "内容信息量充足，且与半导体供需判断相关。",
                        "risk_flags": [],
                    },
                    "industry_relevance": [
                        {
                            "industry_id": "semiconductor",
                            "relationship": "direct",
                            "relevance_score": 0.9,
                            "reason_summary": "文章直接涉及半导体供应链和存储需求变化。",
                        }
                    ],
                    "structured_news": {
                        "canonical_title": "HBM 需求变化影响存储供应链",
                        "short_summary": "文章指出 HBM 需求继续上升，可能影响存储厂商产能和先进封装供应。",
                        "bullet_summary": ["HBM 需求上升。"],
                        "event_type": "supply_demand",
                        "event_type_label": "供需变化",
                        "tags": [{"code": "memory", "label": "存储"}],
                        "entities": ["HBM"],
                        "companies": [],
                        "tickers": [],
                        "technologies": ["HBM"],
                        "products": ["memory"],
                        "locations": [],
                        "numbers": [],
                        "time_horizon": "near_term",
                        "source_facts": ["Fact from article."],
                        "uncertainties": [],
                    },
                    "routing": {
                        "target_industries": ["semiconductor"],
                        "target_topics": ["memory"],
                        "priority": "high",
                        "requires_deep_analysis": True,
                        "requires_human_review": False,
                        "dedupe_key_hint": "https://example.com/article",
                        "reason_summary": "该事件可能改变半导体存储链条的供需判断。",
                        "next_step_hint": "交给半导体行业 MainAgent 做供需和标的影响分析。",
                    },
                    "audit": {
                        "reason_summary": "基于标题和正文中的 HBM 需求证据判定为直接相关。",
                        "evidence_field_refs": ["article.title", "article.body_excerpt"],
                        "schema_validation_status": "valid",
                        "failure_code": None,
                        "safe_error_summary": None,
                        "source_language": "en",
                        "output_language": "zh-CN",
                    },
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ),
            "context_json:",
            json.dumps(context_json, ensure_ascii=True, separators=(",", ":")),
        ]
    )


def _json_default(value: object):
    if isinstance(value, tuple):
        return list(value)
    mapping = getattr(value, "items", None)
    if callable(mapping):
        return dict(value.items())
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
