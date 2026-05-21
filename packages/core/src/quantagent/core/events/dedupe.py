from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from quantagent.core.events.dto import RawEventDraft


@dataclass(frozen=True)
class DedupeIdentity:
    key: str
    reason: str
    content_hash: str | None = None
    canonical_url: str | None = None


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    return url.strip()


def hash_content(content: str | None) -> str | None:
    if not content:
        return None
    normalized = " ".join(content.split())
    if not normalized:
        return None
    return sha256(normalized.encode("utf-8")).hexdigest()


def build_dedupe_identity(event: RawEventDraft) -> DedupeIdentity:
    if event.external_id:
        return DedupeIdentity(
            key=f"{event.source_plugin_id}:external:{event.external_id}",
            reason="source_plugin_id+external_id",
        )

    canonical_url = normalize_url(event.canonical_url or event.url)
    content_hash = hash_content(event.content or event.title)
    if canonical_url and content_hash:
        return DedupeIdentity(
            key=f"{event.source_plugin_id}:url_content:{canonical_url}:{content_hash}",
            reason="source_plugin_id+canonical_url+content_hash",
            content_hash=content_hash,
            canonical_url=canonical_url,
        )

    if event.dedupe_hint:
        return DedupeIdentity(
            key=f"{event.source_plugin_id}:hint:{event.dedupe_hint}",
            reason="source_plugin_id+dedupe_hint",
        )

    fallback_hash = hash_content(f"{event.title}:{event.captured_at.isoformat()}")
    return DedupeIdentity(
        key=f"{event.source_plugin_id}:fallback:{fallback_hash}",
        reason="source_plugin_id+title+captured_at",
        content_hash=fallback_hash,
    )

