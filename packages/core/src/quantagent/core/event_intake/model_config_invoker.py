from __future__ import annotations

import asyncio
import json
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
    service: ModelConfigService
    preset_key: ModelPresetKey = ModelPresetKey.ECONOMY_TEXT

    async def invoke(
        self,
        *,
        context: IndustryEventContextV1,
        output_schema: str,
    ) -> StructuredModelInvocation:
        request_id = context.trace.request_id
        trace_id = context.trace.correlation_id or context.trace.request_id
        user_prompt = _build_user_prompt(context=context, output_schema=output_schema)
        # provider 请求当前仍走同步 HTTP client，这里切到线程执行，避免 worker event loop 被单次模型调用阻塞。
        call_result, invocation = await asyncio.to_thread(
            self.service.invoke_structured_json,
            preset_key=self.preset_key,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
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
                    },
                    "industry_relevance": [
                        {
                            "industry_id": "semiconductor",
                            "relationship": "direct",
                            "relevance_score": 0.9,
                            "reason_summary": "Short reason.",
                        }
                    ],
                    "structured_news": {
                        "canonical_title": "Article title",
                        "short_summary": "One sentence summary.",
                        "bullet_summary": ["Bullet 1"],
                        "event_type": "supply_demand",
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
                    },
                    "audit": {
                        "reason_summary": "Short audit reason.",
                        "evidence_field_refs": ["article.title", "article.body_excerpt"],
                        "schema_validation_status": "valid",
                        "failure_code": None,
                        "safe_error_summary": None,
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
