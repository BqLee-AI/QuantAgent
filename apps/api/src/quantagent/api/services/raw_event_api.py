from __future__ import annotations

import base64
import binascii
import json

from fastapi import Request
from sqlalchemy.orm import Session

from quantagent.api.http.errors import NotFoundError
from quantagent.api.schemas.raw_events import RawEventDetailResponse, RawEventSummaryResponse
from quantagent.core.db.repositories.raw_event_repository import RawEventRepository


class RawEventQueryService:
    def __init__(self, *, session: Session, request: Request) -> None:
        self._repository = RawEventRepository(session)
        self._request = request

    def list_raw_events(
        self,
        *,
        source_plugin_id: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[RawEventSummaryResponse], str | None]:
        items, next_cursor = self._repository.list_for_api(
            source_plugin_id=source_plugin_id,
            cursor=_decode_cursor(cursor),
            limit=limit,
        )
        return ([_to_summary(item) for item in items], _encode_cursor(next_cursor))

    def get_raw_event(self, raw_event_id: str) -> RawEventDetailResponse:
        item = self._repository.get(raw_event_id)
        if item is None:
            raise NotFoundError("RawEvent not found", details={"raw_event_id": raw_event_id})
        return _to_detail(item)


def _to_summary(item) -> RawEventSummaryResponse:
    content_preview = None
    if isinstance(item.content, str) and item.content.strip():
        content_preview = item.content[:280].rstrip()
    return RawEventSummaryResponse(
        raw_event_id=item.raw_event_id,
        source_plugin_id=item.source_plugin_id,
        external_id=item.external_id,
        canonical_url=item.canonical_url,
        title=item.title,
        author=item.author,
        published_at=item.published_at,
        first_captured_at=item.first_captured_at,
        last_captured_at=item.last_captured_at,
        dedupe_strategy=item.dedupe_strategy,
        duplicate_capture_count=item.duplicate_capture_count,
        first_binding_id=item.first_binding_id,
        first_run_id=item.first_run_id,
        content_preview=content_preview,
        metadata_summary=dict(item.metadata_json or {}),
    )


def _to_detail(item) -> RawEventDetailResponse:
    return RawEventDetailResponse(
        raw_event_id=item.raw_event_id,
        source_plugin_id=item.source_plugin_id,
        external_id=item.external_id,
        canonical_url=item.canonical_url,
        title=item.title,
        content=item.content,
        author=item.author,
        published_at=item.published_at,
        first_captured_at=item.first_captured_at,
        last_captured_at=item.last_captured_at,
        dedupe_strategy=item.dedupe_strategy,
        duplicate_capture_count=item.duplicate_capture_count,
        first_binding_id=item.first_binding_id,
        first_run_id=item.first_run_id,
        metadata=dict(item.metadata_json or {}),
        raw_payload=dict(item.raw_payload or {}),
    )


def _encode_cursor(payload: dict[str, str] | None) -> str | None:
    if payload is None:
        return None
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str | None) -> dict[str, str] | None:
    if cursor is None:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeEncodeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("invalid cursor") from exc
    if not isinstance(payload, dict):
        raise ValueError("cursor must decode to an object")
    return {str(key): str(value) for key, value in payload.items()}
