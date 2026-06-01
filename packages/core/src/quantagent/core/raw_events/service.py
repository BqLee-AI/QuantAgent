from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM
from quantagent.core.db.repositories.raw_event_capture_repository import RawEventCaptureRepository
from quantagent.core.db.repositories.raw_event_repository import RawEventRepository
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.events.codec import REDACTED, is_sensitive_key, sanitize_mapping, sanitize_string
from quantagent.core.raw_events.models import (
    PersistSourceFetchResultSummary,
    RawEventCaptureRecord,
    RawEventDedupeStrategy,
    RawEventPersistResult,
    RawEventRecord,
)
from quantagent.plugin_sdk import SourceFetchResult
from quantagent.plugin_sdk.io import SourceItemDraft

MAX_RAW_PAYLOAD_BYTES = 128 * 1024
RAW_PAYLOAD_ALLOWED_KEYS = frozenset(
    {
        "body",
        "description",
        "excerpt",
        "feed",
        "headers",
        "language",
        "links",
        "provider",
        "provider_item_id",
        "published_at",
        "summary",
        "tags",
        "title",
        "url",
    }
)
RAW_CAPTURE_STATUS_CAPTURED = "captured"
METADATA_ALLOWED_KEYS = frozenset(
    {
        "batch_id",
        "canonical_url",
        "correlation_id",
        "feed",
        "item_index",
        "provider",
        "provider_dedupe_hint",
        "provider_item_id",
        "request_id",
        "source",
        "trace_id",
    }
)


class RawEventOwnershipError(ValueError):
    """归属链路不一致时拒绝入库，避免 run / binding 关系被后续流程误用。"""


class RawEventDedupeError(ValueError):
    """缺少稳定去重原料时拒绝入库，避免不同 source 自行发明去重规则。"""


class RawEventPayloadError(ValueError):
    """原始 payload 超出受控边界时拒绝入库，避免不受控大对象和敏感信息入库。"""


class RawEventService:
    def __init__(
        self,
        *,
        raw_event_repository: RawEventRepository,
        raw_event_capture_repository: RawEventCaptureRepository,
        source_binding_repository: SourceBindingRepository,
        scheduler_run_repository: SchedulerRunRepository,
        now_factory: Callable[[], datetime] | None = None,
        raw_event_id_factory: Callable[[], str] | None = None,
        capture_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._raw_event_repository = raw_event_repository
        self._raw_event_capture_repository = raw_event_capture_repository
        self._source_binding_repository = source_binding_repository
        self._scheduler_run_repository = scheduler_run_repository
        self._now_factory = now_factory or _utcnow
        self._raw_event_id_factory = raw_event_id_factory or _default_raw_event_id
        self._capture_id_factory = capture_id_factory or _default_capture_id

    def persist_source_fetch_result(
        self,
        *,
        source_plugin_id: str,
        result: SourceFetchResult,
        source_binding_id: str | None = None,
        scheduler_run_id: str | None = None,
    ) -> PersistSourceFetchResultSummary:
        ownership = self._resolve_ownership(
            source_plugin_id=source_plugin_id,
            source_binding_id=source_binding_id,
            scheduler_run_id=scheduler_run_id,
        )
        persisted: list[RawEventPersistResult] = []
        for item in result.items:
            persisted.append(
                self._persist_item(
                    source_plugin_id=source_plugin_id,
                    source_binding_id=ownership.binding_id,
                    scheduler_run_id=scheduler_run_id,
                    request_id=ownership.request_id,
                    item=item,
                )
            )
        return PersistSourceFetchResultSummary(items=tuple(persisted))

    def _resolve_ownership(
        self,
        *,
        source_plugin_id: str,
        source_binding_id: str | None,
        scheduler_run_id: str | None,
    ) -> _ResolvedOwnership:
        resolved_binding_id = source_binding_id
        request_id: str | None = None
        if source_binding_id is not None:
            binding = self._source_binding_repository.get(source_binding_id)
            if binding is None:
                raise RawEventOwnershipError(f"Unknown source binding: {source_binding_id}")
            if binding.source_plugin_id != source_plugin_id:
                raise RawEventOwnershipError("source binding plugin_id does not match raw event source_plugin_id")
        if scheduler_run_id is None:
            return _ResolvedOwnership(binding_id=resolved_binding_id, request_id=None)
        run = self._scheduler_run_repository.get(scheduler_run_id)
        if run is None:
            raise RawEventOwnershipError(f"Unknown scheduler run: {scheduler_run_id}")
        if run.source_plugin_id != source_plugin_id:
            raise RawEventOwnershipError("scheduler run plugin_id does not match raw event source_plugin_id")
        if resolved_binding_id is None:
            resolved_binding_id = run.binding_id
        elif run.binding_id != resolved_binding_id:
            raise RawEventOwnershipError("scheduler run binding_id does not match raw event source_binding_id")
        request_id = run.request_id
        return _ResolvedOwnership(binding_id=resolved_binding_id, request_id=request_id)

    def _persist_item(
        self,
        *,
        source_plugin_id: str,
        source_binding_id: str | None,
        scheduler_run_id: str | None,
        request_id: str | None,
        item: SourceItemDraft,
    ) -> RawEventPersistResult:
        canonical_url = _canonicalize_url(_metadata_string(item.metadata, "canonical_url") or item.url)
        published_at = _parse_datetime(item.published_at)
        captured_at = _parse_datetime(item.captured_at) or self._now_factory()
        content_hash = _content_hash(content=item.content, title=item.title)
        dedupe = _build_dedupe_identity(
            source_plugin_id=source_plugin_id,
            external_id=item.external_id,
            canonical_url=canonical_url,
            content_hash=content_hash,
            metadata=item.metadata,
        )
        payload = _prepare_raw_payload(item.raw_payload)
        metadata = _project_persisted_metadata(item.metadata, payload_truncated=payload.truncated)

        existing, created = self._raw_event_repository.get_or_create_by_canonical_identity(
            RawEventORM(
                raw_event_id=self._raw_event_id_factory(),
                source_plugin_id=source_plugin_id,
                external_id=item.external_id,
                canonical_url=canonical_url,
                title=item.title,
                content=item.content,
                author=item.author,
                published_at=published_at,
                first_captured_at=captured_at,
                last_captured_at=captured_at,
                raw_payload=payload.payload,
                metadata_json=metadata,
                canonical_dedupe_key=dedupe.key,
                dedupe_strategy=dedupe.strategy.value,
                content_hash=content_hash,
                first_binding_id=source_binding_id,
                first_run_id=scheduler_run_id,
                duplicate_capture_count=0,
            )
        )

        capture_dedupe_key = _build_capture_dedupe_key(
            scheduler_run_id=scheduler_run_id,
            source_binding_id=source_binding_id,
            raw_event_id=existing.raw_event_id,
            captured_at=captured_at,
        )
        duplicate_capture = self._raw_event_capture_repository.get_by_capture_dedupe_key(capture_dedupe_key)
        if duplicate_capture is not None:
            return RawEventPersistResult(
                raw_event=_to_record(existing),
                capture=_to_capture_record(duplicate_capture),
                created=False,
            )

        capture, capture_created = self._raw_event_capture_repository.get_or_create_by_capture_dedupe_key(
            RawEventCaptureORM(
                capture_id=self._capture_id_factory(),
                raw_event_id=existing.raw_event_id,
                source_plugin_id=source_plugin_id,
                source_binding_id=source_binding_id,
                scheduler_run_id=scheduler_run_id,
                capture_dedupe_key=capture_dedupe_key,
                capture_status=RAW_CAPTURE_STATUS_CAPTURED,
                captured_at=captured_at,
                request_id=request_id,
                metadata_json=metadata,
            )
        )
        if not capture_created:
            return RawEventPersistResult(
                raw_event=_to_record(existing),
                capture=_to_capture_record(capture),
                created=False,
            )
        if not created:
            existing.last_captured_at = max(_ensure_utc(existing.last_captured_at), _ensure_utc(captured_at))
            existing.title = existing.title or item.title
            existing.content = existing.content or item.content
            existing.author = existing.author or item.author
            existing.canonical_url = existing.canonical_url or canonical_url
            existing.external_id = existing.external_id or item.external_id
            existing.published_at = existing.published_at or published_at
            if not existing.raw_payload and payload.payload:
                existing.raw_payload = payload.payload
            if not existing.metadata_json and metadata:
                existing.metadata_json = metadata
            existing = self._raw_event_repository.save(existing)
            existing = self._raw_event_repository.increment_duplicate_capture_count(existing)
        return RawEventPersistResult(
            raw_event=_to_record(existing),
            capture=_to_capture_record(capture),
            created=created,
        )


class _ResolvedOwnership:
    def __init__(self, *, binding_id: str | None, request_id: str | None) -> None:
        self.binding_id = binding_id
        self.request_id = request_id


def _to_record(raw_event: RawEventORM) -> RawEventRecord:
    return RawEventRecord(
        raw_event_id=raw_event.raw_event_id,
        source_plugin_id=raw_event.source_plugin_id,
        external_id=raw_event.external_id,
        canonical_url=raw_event.canonical_url,
        title=raw_event.title,
        content=raw_event.content,
        author=raw_event.author,
        published_at=raw_event.published_at,
        first_captured_at=raw_event.first_captured_at,
        last_captured_at=raw_event.last_captured_at,
        raw_payload=dict(raw_event.raw_payload or {}),
        metadata=dict(raw_event.metadata_json or {}),
        canonical_dedupe_key=raw_event.canonical_dedupe_key,
        dedupe_strategy=RawEventDedupeStrategy(raw_event.dedupe_strategy),
        content_hash=raw_event.content_hash,
        first_binding_id=raw_event.first_binding_id,
        first_run_id=raw_event.first_run_id,
        duplicate_capture_count=raw_event.duplicate_capture_count,
        created_at=raw_event.created_at,
        updated_at=raw_event.updated_at,
    )


def _to_capture_record(capture: RawEventCaptureORM) -> RawEventCaptureRecord:
    return RawEventCaptureRecord(
        capture_id=capture.capture_id,
        raw_event_id=capture.raw_event_id,
        source_plugin_id=capture.source_plugin_id,
        source_binding_id=capture.source_binding_id,
        scheduler_run_id=capture.scheduler_run_id,
        capture_dedupe_key=capture.capture_dedupe_key,
        capture_status=capture.capture_status,
        captured_at=capture.captured_at,
        request_id=capture.request_id,
        metadata=dict(capture.metadata_json or {}),
        created_at=capture.created_at,
    )


class _PreparedPayload:
    def __init__(self, *, payload: dict[str, object], truncated: bool) -> None:
        self.payload = payload
        self.truncated = truncated


class _DedupeIdentity:
    def __init__(self, *, key: str, strategy: RawEventDedupeStrategy) -> None:
        self.key = key
        self.strategy = strategy


def _build_dedupe_identity(
    *,
    source_plugin_id: str,
    external_id: str | None,
    canonical_url: str | None,
    content_hash: str | None,
    metadata: Mapping[str, object],
) -> _DedupeIdentity:
    normalized_external_id = _normalized_text(external_id)
    if normalized_external_id is not None:
        return _DedupeIdentity(
            key=_sha256_key("external_id", source_plugin_id, normalized_external_id),
            strategy=RawEventDedupeStrategy.EXTERNAL_ID,
        )
    normalized_url = _normalized_text(canonical_url)
    if normalized_url is not None and content_hash is not None:
        return _DedupeIdentity(
            key=_sha256_key("canonical_url_content", source_plugin_id, normalized_url, content_hash),
            strategy=RawEventDedupeStrategy.CANONICAL_URL_CONTENT,
        )
    dedupe_hint = _normalized_text(_metadata_string(metadata, "provider_dedupe_hint") or _metadata_string(metadata, "dedupe_hint"))
    if dedupe_hint is not None:
        return _DedupeIdentity(
            key=_sha256_key("source_hint", source_plugin_id, dedupe_hint),
            strategy=RawEventDedupeStrategy.SOURCE_HINT,
        )
    raise RawEventDedupeError(
        "raw event requires external_id, canonical_url + content_hash, or metadata.provider_dedupe_hint for dedupe"
    )


def _prepare_raw_payload(raw_payload: Mapping[str, object]) -> _PreparedPayload:
    sanitized = _materialize_json_object(sanitize_mapping(raw_payload))
    if _json_size_bytes(sanitized) <= MAX_RAW_PAYLOAD_BYTES:
        return _PreparedPayload(payload=sanitized, truncated=False)
    allowlisted = {key: value for key, value in sanitized.items() if key in RAW_PAYLOAD_ALLOWED_KEYS}
    if _json_size_bytes(allowlisted) <= MAX_RAW_PAYLOAD_BYTES:
        allowlisted["payload_truncated"] = True
        return _PreparedPayload(payload=allowlisted, truncated=True)
    raise RawEventPayloadError("raw payload exceeds 128 KiB after allowlisted trimming")


def _project_persisted_metadata(metadata: Mapping[str, object], *, payload_truncated: bool) -> dict[str, object]:
    # metadata 入库只保留追踪和去重所需的最小投影，避免完整插件上下文或私有策略长期落库。
    projected = {key: value for key, value in metadata.items() if key in METADATA_ALLOWED_KEYS}
    sanitized = _materialize_json_object(sanitize_mapping(projected))
    if payload_truncated:
        sanitized["payload_truncated"] = True
    return sanitized


def _build_capture_dedupe_key(
    *,
    scheduler_run_id: str | None,
    source_binding_id: str | None,
    raw_event_id: str,
    captured_at: datetime,
) -> str:
    if scheduler_run_id is not None:
        return _sha256_key("run_capture", scheduler_run_id, raw_event_id)
    # 无 run_id 时仍保留最小 capture ledger；captured_at 进入 key 以避免不同批次被错误幂等化。
    return _sha256_key(
        "binding_capture",
        source_binding_id or "",
        raw_event_id,
        _ensure_utc(captured_at).isoformat(),
    )


def _json_size_bytes(value: Mapping[str, object]) -> int:
    return len(json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8"))


def _default_raw_event_id() -> str:
    return f"rawevt_{uuid4().hex}"


def _default_capture_id() -> str:
    return f"rawevtcap_{uuid4().hex}"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sha256_key(*parts: str) -> str:
    joined = "\u241f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _content_hash(*, content: str | None, title: str | None) -> str | None:
    normalized = _normalized_text(content) or _normalized_text(title)
    if normalized is None:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalized_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _metadata_string(metadata: Mapping[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _materialize_json_object(value: Mapping[str, object]) -> dict[str, object]:
    return {str(key): _materialize_json_value(item) for key, item in value.items()}


def _materialize_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _materialize_json_object(value)
    if isinstance(value, tuple | list):
        return [_materialize_json_value(item) for item in value]
    return value


def _canonicalize_url(value: str | None) -> str | None:
    normalized = _normalized_text(value)
    if normalized is None:
        return None
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        return sanitize_string(normalized)
    if not parsed.scheme and not parsed.netloc:
        return sanitize_string(normalized)
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    sanitized_query = _sanitize_query(parsed.query)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, sanitized_query, ""))


def _sanitize_query(query: str) -> str:
    if not query:
        return ""
    safe_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        if is_sensitive_key(key):
            continue
        if value == REDACTED:
            continue
        safe_pairs.append((key, sanitize_string(value)))
    return urlencode(safe_pairs, doseq=True)


def _parse_datetime(value: str | None) -> datetime | None:
    normalized = _normalized_text(value)
    if normalized is None:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
