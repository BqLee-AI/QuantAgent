from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from quantagent.agent.artifacts.models import ArtifactKind, ArtifactRef


@dataclass(frozen=True)
class StoredArtifact:
    ref: ArtifactRef
    payload: Mapping[str, Any]


class ArtifactStore(Protocol):
    def put(
        self,
        *,
        kind: ArtifactKind,
        producer_id: str,
        payload: Mapping[str, Any],
        safe_summary: str,
        created_from_ids: list[str] | None = None,
        confidence_score: float | None = None,
    ) -> ArtifactRef: ...

    def get(self, artifact_id: str) -> StoredArtifact: ...

    def list_for_run(self) -> list[ArtifactRef]: ...


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._artifacts: dict[str, StoredArtifact] = {}

    def put(
        self,
        *,
        kind: ArtifactKind,
        producer_id: str,
        payload: Mapping[str, Any],
        safe_summary: str,
        created_from_ids: list[str] | None = None,
        confidence_score: float | None = None,
    ) -> ArtifactRef:
        artifact_id = f"artifact_{uuid4().hex}"
        # 安全边界：store 只接受调用方已经脱敏的 payload，不保存 provider raw response 或 CoT。
        ref = ArtifactRef(
            artifact_id=artifact_id,
            kind=kind,
            producer_id=producer_id,
            safe_summary=safe_summary,
            created_from_ids=created_from_ids or [],
            confidence_score=confidence_score,
        )
        self._artifacts[artifact_id] = StoredArtifact(ref=ref, payload=dict(payload))
        return ref

    def get(self, artifact_id: str) -> StoredArtifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise KeyError(f"artifact not found: {artifact_id}") from exc

    def list_for_run(self) -> list[ArtifactRef]:
        return [artifact.ref for artifact in self._artifacts.values()]
