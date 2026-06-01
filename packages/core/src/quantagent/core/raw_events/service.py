from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import hashlib
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.repositories.raw_event_repository import RawEventRepository
from quantagent.core.db.repositories.scheduler_run_repository import SchedulerRunRepository
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.events.codec import sanitize_mapping
from quantagent.core.raw_events.models import (
    PersistSourceFetchResultSummary,
    RawEventDedupeStrategy,
    RawEventPersistResult,
    RawEventRecord,
)
from quantagent.plugin_sdk import SourceFetchResult
from quantagent.plugin_sdk.io import SourceItemDraft


class RawEventOwnershipError(ValueError):
    """归属链路不一致时拒绝入库，避免 run / binding 关系被后续流程误用。"""


class RawEventDedupeError(ValueError):
    """缺少稳定去重原料时拒绝入库，避免不同 source 自行发明去重规则。"""


class RawEventService:
    def __init__(
        self,
        *,
        raw_event_repository: RawEventRepository,
        source_binding_repository: SourceBindingRepository,
        scheduler_run_repository: SchedulerRunRepository,
        now_factory: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._raw_event_repository = raw_event_repository
        self._source_binding_repository = source_binding_repository
        self._scheduler_run_repository = scheduler_run_repository
        self._now_factory = now_factory or _utcnow
        self._id_factory = id_factory or _default_raw_event_id

    def persist_source_fetch_result(
        self,
        *,
        source_plugin_id: str,
        result: SourceFetchResult,
        source_binding_id: str | None = None,
        scheduler_run_id: str | None = None,
    ) -> PersistSourceFetchResultSummary:
        resolved_binding_id = self._resolve_ownership(
            source_plugin_id=source_plugin_id,
            source_binding_id=source_binding_id,
            scheduler_run_id=scheduler_run_id,
        )
        persisted: list[RawEventPersistResult] = []
        for item in result.items:
            persisted.append(
                self._persist_item(
                    source_plugin_id=source_plugin_id,
                    source_binding_id=resolved_binding_id,
                    scheduler_run_id=scheduler_run_id,
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
    ) -> str | None:
        resolved_binding_id = source_binding_id
        if source_binding_id is not None:
            binding = self._source_binding_repository.get(source_binding_id)
            if binding is None:
                raise RawEventOwnershipError(f"Unknown source binding: {source_binding_id}")
            if binding.source_plugin_id != source_plugin_id:
                raise RawEventOwnershipError("source binding plugin_id does not match raw event source_plugin_id")
        if scheduler_run_id is None:
            return resolved_binding_id
        run = self._scheduler_run_repository.get(scheduler_run_id)
        if run is None:
            raise RawEventOwnershipError(f"Unknown scheduler run: {scheduler_run_id}")
        if run.source_plugin_id != source_plugin_id:
            raise RawEventOwnershipError("scheduler run plugin_id does not match raw event source_plugin_id")
        if resolved_binding_id is None:
            resolved_binding_id = run.binding_id
        elif run.binding_id != resolved_binding_id:
            raise RawEventOwnershipError("scheduler run binding_id does not match raw event source_binding_id")
        return resolved_binding_id

    def _persist_item(
        self,
        *,
        source_plugin_id: str,
        source_binding_id: str | None,
        scheduler_run_id: str | None,
        item: SourceItemDraft,
    ) -> RawEventPersistResult:
        canonical_url = _canonicalize_url(_metadata_string(item.metadata, "canonical_url") or item.url)
        published_at = _parse_datetime(item.published_at)
        captured_at = _parse_datetime(item.captured_at) or self._now_factory()
        raw_payload = dict(sanitize_mapping(item.raw_payload))
        metadata = dict(sanitize_mapping(item.metadata))
        content_hash = _content_hash(content=item.content, title=item.title)
        dedupe = _build_dedupe_identity(
            source_plugin_id=source_plugin_id,
            external_id=item.external_id,
            canonical_url=canonical_url,
            content_hash=content_hash,
            metadata=item.metadata,
        )
        existing = self._raw_event_repository.get_by_dedupe_key(dedupe.key)
        if existing is not None:
            # V1 只保留 canonical row，并在重复命中时更新最近一次命中时间和补全缺失字段，
            # 这样 #217/#224 后续读取不会被同一 source item 的重复行污染。
            existing.last_seen_at = max(_ensure_utc(existing.last_seen_at), _ensure_utc(captured_at))
            existing.duplicate_count += 1
            if existing.scheduler_run_id is None and scheduler_run_id is not None:
                existing.scheduler_run_id = scheduler_run_id
            if existing.source_binding_id is None and source_binding_id is not None:
                existing.source_binding_id = source_binding_id
            existing.title = existing.title or item.title
            existing.content = existing.content or item.content
            existing.author = existing.author or item.author
            existing.canonical_url = existing.canonical_url or canonical_url
            existing.external_id = existing.external_id or item.external_id
            existing.published_at = existing.published_at or published_at
            if not existing.raw_payload and raw_payload:
                existing.raw_payload = raw_payload
            if not existing.metadata_json and metadata:
                existing.metadata_json = metadata
            saved = self._raw_event_repository.save(existing)
            return RawEventPersistResult(raw_event=_to_record(saved), created=False)
        created = self._raw_event_repository.create(
            RawEventORM(
                raw_event_id=self._id_factory(),
                source_plugin_id=source_plugin_id,
                source_binding_id=source_binding_id,
                scheduler_run_id=scheduler_run_id,
                external_id=item.external_id,
                canonical_url=canonical_url,
                title=item.title,
                content=item.content,
                author=item.author,
                published_at=published_at,
                captured_at=captured_at,
                last_seen_at=captured_at,
                raw_payload=raw_payload,
                metadata_json=metadata,
                dedupe_key=dedupe.key,
                dedupe_strategy=dedupe.strategy.value,
                content_hash=content_hash,
            )
        )
        return RawEventPersistResult(raw_event=_to_record(created), created=True)


def _to_record(raw_event: RawEventORM) -> RawEventRecord:
    return RawEventRecord(
        raw_event_id=raw_event.raw_event_id,
        source_plugin_id=raw_event.source_plugin_id,
        source_binding_id=raw_event.source_binding_id,
        scheduler_run_id=raw_event.scheduler_run_id,
        external_id=raw_event.external_id,
        canonical_url=raw_event.canonical_url,
        title=raw_event.title,
        content=raw_event.content,
        author=raw_event.author,
        published_at=raw_event.published_at,
        captured_at=raw_event.captured_at,
        last_seen_at=raw_event.last_seen_at,
        raw_payload=dict(raw_event.raw_payload or {}),
        metadata=dict(raw_event.metadata_json or {}),
        dedupe_key=raw_event.dedupe_key,
        dedupe_strategy=RawEventDedupeStrategy(raw_event.dedupe_strategy),
        content_hash=raw_event.content_hash,
        duplicate_count=raw_event.duplicate_count,
        created_at=raw_event.created_at,
        updated_at=raw_event.updated_at,
    )


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
    dedupe_hint = _normalized_text(_metadata_string(metadata, "dedupe_hint"))
    if dedupe_hint is not None:
        return _DedupeIdentity(
            key=_sha256_key("source_hint", source_plugin_id, dedupe_hint),
            strategy=RawEventDedupeStrategy.SOURCE_HINT,
        )
    raise RawEventDedupeError(
        "raw event requires external_id, canonical_url + content_hash, or metadata.dedupe_hint for dedupe"
    )


def _default_raw_event_id() -> str:
    return f"rawevt_{uuid4().hex}"


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


def _canonicalize_url(value: str | None) -> str | None:
    normalized = _normalized_text(value)
    if normalized is None:
        return None
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        return normalized
    if not parsed.scheme and not parsed.netloc:
        return normalized
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


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
