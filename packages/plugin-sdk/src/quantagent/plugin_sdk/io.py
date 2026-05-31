from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, TypeAlias, runtime_checkable

from quantagent.plugin_sdk.runtime import PluginRuntimeError

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]

DTO_VALIDATION_ERROR_CODE = "PLUGIN_DTO_VALIDATION_FAILED"


def dto_validation_error(
    message: str,
    *,
    field_name: str | None = None,
    stage: str = "invoke",
    details: Mapping[str, JsonValue] | None = None,
) -> PluginRuntimeError:
    # Keep validation errors generic so runtime wrappers can surface structure without leaking payload contents.
    error_details = dict(details or {})
    if field_name is not None:
        error_details.setdefault("field", field_name)
    return PluginRuntimeError(
        code=DTO_VALIDATION_ERROR_CODE,
        message=message,
        stage=stage,
        details=freeze_json_mapping(error_details),
    )


def freeze_json_mapping(value: Mapping[str, Any] | None = None, *, stage: str = "invoke") -> JsonObject:
    normalized = {
        _validate_mapping_key(key, stage=stage): freeze_json_value(item, stage=stage)
        for key, item in (value or {}).items()
    }
    return MappingProxyType(normalized)


def freeze_json_value(value: Any, *, stage: str = "invoke") -> JsonValue:
    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        raise dto_validation_error(
            "Plugin DTO numbers must be finite JSON-safe values.",
            stage=stage,
            details={"value_type": type(value).__name__},
        )
    if isinstance(value, Mapping):
        return freeze_json_mapping(value, stage=stage)
    if isinstance(value, list | tuple):
        return tuple(freeze_json_value(item, stage=stage) for item in value)
    raise dto_validation_error(
        "Plugin DTO values must be JSON-safe scalars, arrays, or objects.",
        stage=stage,
        details={"value_type": type(value).__name__},
    )


def to_json_value(value: JsonValue) -> Any:
    if isinstance(value, Mapping):
        return {key: to_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_json_value(item) for item in value]
    return value


@runtime_checkable
class PluginInput(Protocol):
    def to_mapping(self) -> dict[str, Any]: ...


@runtime_checkable
class PluginResult(Protocol):
    def to_mapping(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SourceFetchInput:
    query: str | None = None
    limit: int | None = None
    cursor: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_optional_string("query", self.query)
        _validate_optional_int("limit", self.limit)
        _validate_optional_string("cursor", self.cursor)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "limit": self.limit,
            "cursor": self.cursor,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_input = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> SourceFetchInput:
        _validate_object(payload, dto_name="SourceFetchInput", stage=stage)
        return cls(
            query=_get_optional_string(payload, "query", stage=stage),
            limit=_get_optional_int(payload, "limit", stage=stage),
            cursor=_get_optional_string(payload, "cursor", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class SourceItemDraft:
    external_id: str | None = None
    url: str | None = None
    title: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: str | None = None
    captured_at: str | None = None
    raw_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_optional_string("external_id", self.external_id)
        _validate_optional_string("url", self.url)
        _validate_optional_string("title", self.title)
        _validate_optional_string("content", self.content)
        _validate_optional_string("author", self.author)
        _validate_optional_string("published_at", self.published_at)
        _validate_optional_string("captured_at", self.captured_at)
        object.__setattr__(self, "raw_payload", freeze_json_mapping(self.raw_payload))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "external_id": self.external_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "published_at": self.published_at,
            "captured_at": self.captured_at,
            "raw_payload": to_json_value(self.raw_payload),
            "metadata": to_json_value(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> SourceItemDraft:
        _validate_object(payload, dto_name="SourceItemDraft", stage=stage)
        return cls(
            external_id=_get_optional_string(payload, "external_id", stage=stage),
            url=_get_optional_string(payload, "url", stage=stage),
            title=_get_optional_string(payload, "title", stage=stage),
            content=_get_optional_string(payload, "content", stage=stage),
            author=_get_optional_string(payload, "author", stage=stage),
            published_at=_get_optional_string(payload, "published_at", stage=stage),
            captured_at=_get_optional_string(payload, "captured_at", stage=stage),
            raw_payload=freeze_json_mapping(_get_optional_mapping(payload, "raw_payload", stage=stage), stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class SourceFetchResult:
    items: tuple[SourceItemDraft, ...] = field(default_factory=tuple)
    next_cursor: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", _freeze_items(self.items))
        _validate_optional_string("next_cursor", self.next_cursor)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "items": [item.to_mapping() for item in self.items],
            "next_cursor": self.next_cursor,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> SourceFetchResult:
        _validate_object(payload, dto_name="SourceFetchResult", stage=stage)
        if "items" not in payload:
            raise dto_validation_error(
                "SourceFetchResult.items is required.",
                field_name="items",
                stage=stage,
            )
        items = payload["items"]
        if not isinstance(items, list | tuple):
            raise dto_validation_error(
                "SourceFetchResult.items must be an array of SourceItemDraft objects.",
                field_name="items",
                stage=stage,
                details={"value_type": type(items).__name__},
            )
        return cls(
            items=tuple(
                item
                if isinstance(item, SourceItemDraft)
                else SourceItemDraft.from_mapping(_require_mapping(item, field_name="items", stage=stage), stage=stage)
                for item in items
            ),
            next_cursor=_get_optional_string(payload, "next_cursor", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class NotificationSendInput:
    channel: str
    text: str
    severity: str | None = None
    recipient: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("channel", self.channel)
        _validate_required_string("text", self.text)
        _validate_optional_string("severity", self.severity)
        _validate_optional_string("recipient", self.recipient)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "text": self.text,
            "severity": self.severity,
            "recipient": self.recipient,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_input = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> NotificationSendInput:
        _validate_object(payload, dto_name="NotificationSendInput", stage=stage)
        return cls(
            channel=_get_required_string(payload, "channel", stage=stage),
            text=_get_required_string(payload, "text", stage=stage),
            severity=_get_optional_string(payload, "severity", stage=stage),
            recipient=_get_optional_string(payload, "recipient", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class NotificationSendResult:
    accepted: bool
    provider_message_id: str | None = None
    retryable: bool = False
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_bool("accepted", self.accepted)
        _validate_optional_string("provider_message_id", self.provider_message_id)
        _validate_bool("retryable", self.retryable)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "provider_message_id": self.provider_message_id,
            "retryable": self.retryable,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> NotificationSendResult:
        _validate_object(payload, dto_name="NotificationSendResult", stage=stage)
        return cls(
            accepted=_get_required_bool(payload, "accepted", stage=stage),
            provider_message_id=_get_optional_string(payload, "provider_message_id", stage=stage),
            retryable=_get_required_bool(payload, "retryable", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@runtime_checkable
class EvidenceLike(Protocol):
    """最小证据契约 — 跨链路解耦接口。

    任何证据来源只需满足 title/url/snippet 三个属性即可传入 AnalysisInput。
    EvidenceItem 天然满足此 Protocol；外部插件也可自行实现。
    与 RuntimePlugin Protocol 风格一致：结构性子类型，不要求继承。
    """

    @property
    def title(self) -> str | None: ...

    @property
    def url(self) -> str | None: ...

    @property
    def snippet(self) -> str | None: ...


@dataclass(frozen=True)
class EvidenceItem:
    """证据检索结果中的单个证据项"""
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    score: float | None = None
    source: str | None = None
    published_at: str | None = None
    favicon_url: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_optional_string("title", self.title)
        _validate_optional_string("url", self.url)
        _validate_optional_string("snippet", self.snippet)
        _validate_optional_float("score", self.score)
        _validate_optional_string("source", self.source)
        _validate_optional_string("published_at", self.published_at)
        _validate_optional_string("favicon_url", self.favicon_url)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "score": self.score,
            "source": self.source,
            "published_at": self.published_at,
            "favicon_url": self.favicon_url,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> EvidenceItem:
        _validate_object(payload, dto_name="EvidenceItem", stage=stage)
        return cls(
            title=_get_optional_string(payload, "title", stage=stage),
            url=_get_optional_string(payload, "url", stage=stage),
            snippet=_get_optional_string(payload, "snippet", stage=stage),
            score=_get_optional_float(payload, "score", stage=stage),
            source=_get_optional_string(payload, "source", stage=stage),
            published_at=_get_optional_string(payload, "published_at", stage=stage),
            favicon_url=_get_optional_string(payload, "favicon_url", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class EvidenceSearchResult:
    """证据检索插件的输出结果"""
    query: str
    results: tuple[EvidenceItem, ...] = field(default_factory=tuple)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("query", self.query)
        object.__setattr__(self, "results", _freeze_evidence_items(self.results))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [item.to_mapping() for item in self.results],
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> EvidenceSearchResult:
        _validate_object(payload, dto_name="EvidenceSearchResult", stage=stage)
        results_raw = payload.get("results", [])
        if not isinstance(results_raw, list | tuple):
            raise dto_validation_error("results must be an array.", field_name="results", stage=stage)
        return cls(
            query=_get_required_string(payload, "query", stage=stage),
            results=tuple(
                item if isinstance(item, EvidenceItem) else EvidenceItem.from_mapping(_require_mapping(item, field_name="results", stage=stage), stage=stage)
                for item in results_raw
            ),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class EvidenceExtractResult:
    """证据内容提取插件的输出结果"""
    url: str
    title: str | None = None
    content: str | None = None
    raw_content: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("url", self.url)
        _validate_optional_string("title", self.title)
        _validate_optional_string("content", self.content)
        _validate_optional_string("raw_content", self.raw_content)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "raw_content": self.raw_content,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> EvidenceExtractResult:
        _validate_object(payload, dto_name="EvidenceExtractResult", stage=stage)
        return cls(
            url=_get_required_string(payload, "url", stage=stage),
            title=_get_optional_string(payload, "title", stage=stage),
            content=_get_optional_string(payload, "content", stage=stage),
            raw_content=_get_optional_string(payload, "raw_content", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class AnalysisInput:
    """分析插件的输入参数。

    evidences 接受满足 EvidenceLike Protocol 的任意对象，
    不强绑定具体 DTO 类型，保持链路松耦合。
    """
    evidences: tuple[EvidenceLike, ...] = field(default_factory=tuple)
    query: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 冻结 evidences 元组，验证所有元素满足 EvidenceLike Protocol
        object.__setattr__(self, "evidences", _freeze_evidence_like(self.evidences))
        _validate_optional_string("query", self.query)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            # EvidenceLike 对象可能是 dataclass 或任意对象，统一走 to_json_value
            "evidences": [
                to_json_value(e.to_mapping()) if hasattr(e, "to_mapping") else to_json_value(e)
                for e in self.evidences
            ],
            "query": self.query,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_input = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> AnalysisInput:
        _validate_object(payload, dto_name="AnalysisInput", stage=stage)
        evidences_raw = payload.get("evidences", [])
        if not isinstance(evidences_raw, list | tuple):
            raise dto_validation_error("evidences must be an array.", field_name="evidences", stage=stage)
        # from_mapping 从 plain mapping 重建，用 EvidenceItem 作为标准载体
        return cls(
            evidences=tuple(
                EvidenceItem.from_mapping(_require_mapping(e, field_name="evidences", stage=stage), stage=stage)
                if not isinstance(e, EvidenceLike)
                else e
                for e in evidences_raw
            ),
            query=_get_optional_string(payload, "query", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class AnalysisResult:
    """分析插件的输出结果"""
    summary: str
    key_facts: tuple[str, ...] = field(default_factory=tuple)
    market_impact: str | None = None
    direction: str | None = None
    confidence: float | None = None
    uncertainty: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("summary", self.summary)
        object.__setattr__(self, "key_facts", _freeze_strings(self.key_facts))
        _validate_optional_string("market_impact", self.market_impact)
        _validate_optional_string("direction", self.direction)
        _validate_optional_float("confidence", self.confidence)
        object.__setattr__(self, "uncertainty", _freeze_strings(self.uncertainty))
        object.__setattr__(self, "evidence_refs", _freeze_strings(self.evidence_refs))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "key_facts": list(self.key_facts),
            "market_impact": self.market_impact,
            "direction": self.direction,
            "confidence": self.confidence,
            "uncertainty": list(self.uncertainty),
            "evidence_refs": list(self.evidence_refs),
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> AnalysisResult:
        _validate_object(payload, dto_name="AnalysisResult", stage=stage)
        return cls(
            summary=_get_required_string(payload, "summary", stage=stage),
            key_facts=_get_optional_string_tuple(payload, "key_facts", stage=stage),
            market_impact=_get_optional_string(payload, "market_impact", stage=stage),
            direction=_get_optional_string(payload, "direction", stage=stage),
            confidence=_get_optional_float(payload, "confidence", stage=stage),
            uncertainty=_get_optional_string_tuple(payload, "uncertainty", stage=stage),
            evidence_refs=_get_optional_string_tuple(payload, "evidence_refs", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class StrategyDraftInput:
    """策略草稿插件的输入参数"""
    analysis: Mapping[str, Any] = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "analysis", freeze_json_mapping(self.analysis))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "analysis": to_json_value(self.analysis),
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_input = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> StrategyDraftInput:
        _validate_object(payload, dto_name="StrategyDraftInput", stage=stage)
        return cls(
            analysis=freeze_json_mapping(_get_optional_mapping(payload, "analysis", stage=stage), stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class StrategyDraftResult:
    """策略草稿插件的输出结果"""
    action: str
    rationale: str
    symbol: str | None = None
    direction: str | None = None
    time_horizon: str | None = None
    risk_notes: tuple[str, ...] = field(default_factory=tuple)
    confidence: float | None = None
    requires_approval: bool = True
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("action", self.action)
        _validate_optional_string("symbol", self.symbol)
        _validate_optional_string("direction", self.direction)
        _validate_optional_string("time_horizon", self.time_horizon)
        _validate_required_string("rationale", self.rationale)
        object.__setattr__(self, "risk_notes", _freeze_strings(self.risk_notes))
        _validate_optional_float("confidence", self.confidence)
        _validate_bool("requires_approval", self.requires_approval)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "symbol": self.symbol,
            "direction": self.direction,
            "time_horizon": self.time_horizon,
            "rationale": self.rationale,
            "risk_notes": list(self.risk_notes),
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> StrategyDraftResult:
        _validate_object(payload, dto_name="StrategyDraftResult", stage=stage)
        return cls(
            action=_get_required_string(payload, "action", stage=stage),
            symbol=_get_optional_string(payload, "symbol", stage=stage),
            direction=_get_optional_string(payload, "direction", stage=stage),
            time_horizon=_get_optional_string(payload, "time_horizon", stage=stage),
            rationale=_get_required_string(payload, "rationale", stage=stage),
            risk_notes=_get_optional_string_tuple(payload, "risk_notes", stage=stage),
            confidence=_get_optional_float(payload, "confidence", stage=stage),
            requires_approval=_get_optional_bool(payload, "requires_approval", default=True, stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class BrokerExecuteInput:
    """经纪商执行插件的输入参数"""
    action: str
    symbol: str
    quantity: float | None = None
    order_type: str | None = None
    price: float | None = None
    dry_run: bool = True
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("action", self.action)
        _validate_required_string("symbol", self.symbol)
        _validate_optional_float("quantity", self.quantity)
        _validate_optional_string("order_type", self.order_type)
        _validate_optional_float("price", self.price)
        _validate_bool("dry_run", self.dry_run)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "price": self.price,
            "dry_run": self.dry_run,
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_input = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> BrokerExecuteInput:
        _validate_object(payload, dto_name="BrokerExecuteInput", stage=stage)
        return cls(
            action=_get_required_string(payload, "action", stage=stage),
            symbol=_get_required_string(payload, "symbol", stage=stage),
            quantity=_get_optional_float(payload, "quantity", stage=stage),
            order_type=_get_optional_string(payload, "order_type", stage=stage),
            price=_get_optional_float(payload, "price", stage=stage),
            dry_run=_get_optional_bool(payload, "dry_run", default=True, stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


@dataclass(frozen=True)
class BrokerExecuteResult:
    """经纪商执行插件的输出结果"""
    status: str
    estimated_order: Mapping[str, Any] | None = None
    validation_errors: tuple[str, ...] = field(default_factory=tuple)
    audit_hints: tuple[str, ...] = field(default_factory=tuple)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_required_string("status", self.status)
        if self.estimated_order is not None:
            object.__setattr__(self, "estimated_order", freeze_json_mapping(self.estimated_order))
        object.__setattr__(self, "validation_errors", _freeze_strings(self.validation_errors))
        object.__setattr__(self, "audit_hints", _freeze_strings(self.audit_hints))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "estimated_order": to_json_value(self.estimated_order) if self.estimated_order is not None else None,
            "validation_errors": list(self.validation_errors),
            "audit_hints": list(self.audit_hints),
            "metadata": to_json_value(self.metadata),
        }

    as_plugin_output = to_mapping

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], *, stage: str = "invoke") -> BrokerExecuteResult:
        _validate_object(payload, dto_name="BrokerExecuteResult", stage=stage)
        order_raw = payload.get("estimated_order")
        return cls(
            status=_get_required_string(payload, "status", stage=stage),
            estimated_order=freeze_json_mapping(_require_mapping(order_raw, field_name="estimated_order", stage=stage), stage=stage) if order_raw is not None else None,
            validation_errors=_get_optional_string_tuple(payload, "validation_errors", stage=stage),
            audit_hints=_get_optional_string_tuple(payload, "audit_hints", stage=stage),
            metadata=freeze_json_mapping(_get_optional_mapping(payload, "metadata", stage=stage), stage=stage),
        )


def _freeze_items(items: tuple[SourceItemDraft, ...] | list[SourceItemDraft]) -> tuple[SourceItemDraft, ...]:
    if not isinstance(items, list | tuple):
        raise dto_validation_error(
            "SourceFetchResult.items must be an array of SourceItemDraft objects.",
            field_name="items",
            details={"value_type": type(items).__name__},
        )
    frozen_items: list[SourceItemDraft] = []
    for item in items:
        if not isinstance(item, SourceItemDraft):
            raise dto_validation_error(
                "SourceFetchResult.items must contain SourceItemDraft instances.",
                field_name="items",
                details={"value_type": type(item).__name__},
            )
        frozen_items.append(item)
    return tuple(frozen_items)


def _freeze_evidence_items(items: tuple[EvidenceItem, ...] | list[EvidenceItem]) -> tuple[EvidenceItem, ...]:
    """冻结 EvidenceItem 元组，验证所有元素都是 EvidenceItem 实例"""
    if not isinstance(items, list | tuple):
        raise dto_validation_error(
            "EvidenceSearchResult.results must be an array of EvidenceItem objects.",
            field_name="results",
            details={"value_type": type(items).__name__},
        )
    frozen_items: list[EvidenceItem] = []
    for item in items:
        if not isinstance(item, EvidenceItem):
            raise dto_validation_error(
                "EvidenceSearchResult.results must contain EvidenceItem instances.",
                field_name="results",
                details={"value_type": type(item).__name__},
            )
        frozen_items.append(item)
    return tuple(frozen_items)


def _freeze_evidence_like(items: tuple[EvidenceLike, ...] | list[EvidenceLike]) -> tuple[EvidenceLike, ...]:
    """冻结 EvidenceLike 元组，验证所有元素满足 Protocol"""
    if not isinstance(items, list | tuple):
        raise dto_validation_error(
            "AnalysisInput.evidences must be an array.",
            field_name="evidences",
            details={"value_type": type(items).__name__},
        )
    for item in items:
        if not isinstance(item, EvidenceLike):
            raise dto_validation_error(
                "evidences must contain objects satisfying EvidenceLike protocol (title, url, snippet).",
                field_name="evidences",
                details={"value_type": type(item).__name__},
            )
    return tuple(items)


def _validate_object(payload: Mapping[str, Any], *, dto_name: str, stage: str) -> None:
    if not isinstance(payload, Mapping):
        raise dto_validation_error(
            f"{dto_name} payload must be an object mapping.",
            stage=stage,
            details={"value_type": type(payload).__name__},
        )


def _validate_mapping_key(key: Any, *, stage: str) -> str:
    if not isinstance(key, str):
        raise dto_validation_error(
            "Plugin DTO object keys must be strings.",
            stage=stage,
            details={"key_type": type(key).__name__},
        )
    return key


def _validate_required_string(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if not isinstance(value, str):
        raise dto_validation_error(
            f"{field_name} must be a string.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _validate_optional_string(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if value is not None and not isinstance(value, str):
        raise dto_validation_error(
            f"{field_name} must be a string or null.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _validate_optional_int(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise dto_validation_error(
            f"{field_name} must be an integer or null.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _validate_bool(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    if not isinstance(value, bool):
        raise dto_validation_error(
            f"{field_name} must be a boolean.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )


def _get_required_string(payload: Mapping[str, Any], field_name: str, *, stage: str) -> str:
    if field_name not in payload:
        raise dto_validation_error(
            f"{field_name} is required.",
            field_name=field_name,
            stage=stage,
        )
    value = payload[field_name]
    _validate_required_string(field_name, value, stage=stage)
    return value


def _get_optional_string(payload: Mapping[str, Any], field_name: str, *, stage: str) -> str | None:
    value = payload.get(field_name)
    _validate_optional_string(field_name, value, stage=stage)
    return value


def _get_optional_int(payload: Mapping[str, Any], field_name: str, *, stage: str) -> int | None:
    value = payload.get(field_name)
    _validate_optional_int(field_name, value, stage=stage)
    return value


def _get_required_bool(payload: Mapping[str, Any], field_name: str, *, stage: str) -> bool:
    if field_name not in payload:
        raise dto_validation_error(
            f"{field_name} is required.",
            field_name=field_name,
            stage=stage,
        )
    value = payload[field_name]
    _validate_bool(field_name, value, stage=stage)
    return value


def _get_optional_bool(payload: Mapping[str, Any], field_name: str, *, default: bool = False, stage: str) -> bool:
    """从 payload 获取可选的布尔字段，缺失时返回 default"""
    if field_name not in payload:
        return default
    value = payload[field_name]
    _validate_bool(field_name, value, stage=stage)
    return value


def _get_optional_mapping(payload: Mapping[str, Any], field_name: str, *, stage: str) -> Mapping[str, Any]:
    value = payload.get(field_name, {})
    return _require_mapping(value, field_name=field_name, stage=stage)


def _require_mapping(value: Any, *, field_name: str, stage: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise dto_validation_error(
        f"{field_name} must be an object mapping.",
        field_name=field_name,
        stage=stage,
        details={"value_type": type(value).__name__},
    )


def _validate_optional_float(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    """验证可选浮点数字段，接受 int 或 float，拒绝 NaN/Inf"""
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise dto_validation_error(
            f"{field_name} must be a number or null.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise dto_validation_error(
            f"{field_name} must be a finite number.",
            field_name=field_name,
            stage=stage,
        )


def _validate_required_float(field_name: str, value: Any, *, stage: str = "invoke") -> None:
    """验证必需浮点数字段，接受 int 或 float，拒绝 NaN/Inf"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise dto_validation_error(
            f"{field_name} must be a number.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise dto_validation_error(
            f"{field_name} must be a finite number.",
            field_name=field_name,
            stage=stage,
        )


def _get_required_float(payload: Mapping[str, Any], field_name: str, *, stage: str) -> float:
    """从 payload 获取必需的浮点数字段"""
    if field_name not in payload:
        raise dto_validation_error(
            f"{field_name} is required.",
            field_name=field_name,
            stage=stage,
        )
    value = payload[field_name]
    _validate_required_float(field_name, value, stage=stage)
    return float(value)


def _get_optional_float(payload: Mapping[str, Any], field_name: str, *, stage: str) -> float | None:
    """从 payload 获取可选的浮点数字段"""
    value = payload.get(field_name)
    _validate_optional_float(field_name, value, stage=stage)
    return float(value) if value is not None else None


def _freeze_strings(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """冻结字符串元组，验证所有元素都是字符串"""
    if not isinstance(values, list | tuple):
        raise dto_validation_error("Expected a list of strings.", details={"value_type": type(values).__name__})
    for item in values:
        if not isinstance(item, str):
            raise dto_validation_error("All items must be strings.", details={"value_type": type(item).__name__})
    return tuple(values)


def _get_optional_string_tuple(payload: Mapping[str, Any], field_name: str, *, stage: str) -> tuple[str, ...]:
    """从 payload 获取可选的字符串元组字段"""
    value = payload.get(field_name, [])
    if not isinstance(value, list | tuple):
        raise dto_validation_error(
            f"{field_name} must be an array of strings.",
            field_name=field_name,
            stage=stage,
            details={"value_type": type(value).__name__},
        )
    return _freeze_strings(value)
