from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import gzip
from pathlib import Path
import shutil
import threading
from time import monotonic

from quantagent.api.observability.files import ParsedLogFile, SUPPORTED_STREAMS, parse_log_file


_DISK_GUARD_CHECK_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True)
class StreamRetentionDays:
    access: int
    app: int
    error: int
    security: int
    audit: int

    def for_stream(self, stream: str) -> int:
        return getattr(self, stream)


@dataclass(frozen=True)
class MaintenanceConfig:
    root_dir: Path
    min_age_seconds: int
    retention_days: StreamRetentionDays
    max_total_bytes: int | None
    min_free_bytes: int | None


@dataclass(frozen=True)
class MaintenanceSummary:
    compressed_files: int = 0
    deleted_files: int = 0
    skipped_files: int = 0


@dataclass(frozen=True)
class DiskGuardState:
    under_pressure: bool
    total_bytes: int
    free_bytes: int
    reason: str | None = None


class DiskGuard:
    def __init__(
        self,
        *,
        config: MaintenanceConfig,
        check_interval_seconds: float = _DISK_GUARD_CHECK_INTERVAL_SECONDS,
    ) -> None:
        self._config = config
        self._check_interval_seconds = check_interval_seconds
        self._lock = threading.Lock()
        self._state = DiskGuardState(under_pressure=False, total_bytes=0, free_bytes=0)
        self._next_refresh_at = 0.0

    def current_state(self, *, force: bool = False) -> DiskGuardState:
        now = monotonic()
        with self._lock:
            if not force and now < self._next_refresh_at:
                return self._state
        state = _compute_disk_guard_state(self._config)
        with self._lock:
            self._state = state
            self._next_refresh_at = monotonic() + self._check_interval_seconds
            return self._state


class LogMaintenanceRuntime:
    def __init__(self, config: MaintenanceConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._disk_guard = DiskGuard(config=config)

    @property
    def disk_guard(self) -> DiskGuard:
        return self._disk_guard

    def run_startup_cleanup(self) -> MaintenanceSummary:
        return self._run_cleanup(now=datetime.now(UTC), active_paths=set(), force_closed_paths=set())

    def run_shutdown_cleanup(self, *, force_closed_paths: set[Path]) -> MaintenanceSummary:
        return self._run_cleanup(now=datetime.now(UTC), active_paths=set(), force_closed_paths=force_closed_paths)

    def _run_cleanup(
        self,
        *,
        now: datetime,
        active_paths: set[Path],
        force_closed_paths: set[Path],
    ) -> MaintenanceSummary:
        with self._lock:
            summary = MaintenanceSummary()
            for parsed in _iter_known_log_files(self._config.root_dir):
                summary = _merge_summary(
                    summary,
                    self._handle_file(
                        parsed,
                        now=now,
                        active_paths=active_paths,
                        force_closed_paths=force_closed_paths,
                    ),
                )
            self._disk_guard.current_state(force=True)
            return summary

    def _handle_file(
        self,
        parsed: ParsedLogFile,
        *,
        now: datetime,
        active_paths: set[Path],
        force_closed_paths: set[Path],
    ) -> MaintenanceSummary:
        if _is_expired(parsed, now=now, retention_days=self._config.retention_days):
            if _is_confidently_closed(
                parsed,
                now=now,
                min_age_seconds=self._config.min_age_seconds,
                active_paths=active_paths,
                force_closed_paths=force_closed_paths,
            ):
                parsed.path.unlink(missing_ok=True)
                return MaintenanceSummary(deleted_files=1)
            return MaintenanceSummary(skipped_files=1)

        if parsed.compressed:
            return MaintenanceSummary()

        if not _is_confidently_closed(
            parsed,
            now=now,
            min_age_seconds=self._config.min_age_seconds,
            active_paths=active_paths,
            force_closed_paths=force_closed_paths,
        ):
            return MaintenanceSummary(skipped_files=1)

        compressed_path = parsed.path.with_suffix(parsed.path.suffix + ".gz")
        if compressed_path.exists():
            return MaintenanceSummary(skipped_files=1)

        with parsed.path.open("rb") as source, gzip.open(compressed_path, "wb") as target:
            shutil.copyfileobj(source, target)
        parsed.path.unlink(missing_ok=True)
        return MaintenanceSummary(compressed_files=1)


def _compute_disk_guard_state(config: MaintenanceConfig) -> DiskGuardState:
    root_dir = config.root_dir
    total_bytes = sum(path.stat().st_size for path in root_dir.rglob("*") if path.is_file()) if root_dir.exists() else 0
    usage_root = root_dir if root_dir.exists() else root_dir.parent
    usage = shutil.disk_usage(usage_root)
    reason: str | None = None
    under_pressure = False
    if config.max_total_bytes is not None and total_bytes >= config.max_total_bytes:
        under_pressure = True
        reason = "max_total_bytes"
    if config.min_free_bytes is not None and usage.free <= config.min_free_bytes:
        under_pressure = True
        reason = reason or "min_free_bytes"
    return DiskGuardState(
        under_pressure=under_pressure,
        total_bytes=total_bytes,
        free_bytes=usage.free,
        reason=reason,
    )


def _iter_known_log_files(root_dir: Path) -> list[ParsedLogFile]:
    if not root_dir.exists():
        return []
    parsed_files: list[ParsedLogFile] = []
    for stream in SUPPORTED_STREAMS:
        stream_dir = root_dir / stream
        if not stream_dir.exists():
            continue
        for path in stream_dir.rglob("*.jsonl*"):
            if not path.is_file():
                continue
            parsed = parse_log_file(path)
            if parsed is not None:
                parsed_files.append(parsed)
    parsed_files.sort(key=lambda item: str(item.path))
    return parsed_files


def _is_confidently_closed(
    parsed: ParsedLogFile,
    *,
    now: datetime,
    min_age_seconds: int,
    active_paths: set[Path],
    force_closed_paths: set[Path],
) -> bool:
    if parsed.path in force_closed_paths:
        return True
    if parsed.path in active_paths:
        return False
    if parsed.date_slice == now.strftime("%Y%m%d"):
        return False
    age_seconds = max(0.0, (now - datetime.fromtimestamp(parsed.path.stat().st_mtime, UTC)).total_seconds())
    return age_seconds >= min_age_seconds


def _is_expired(
    parsed: ParsedLogFile,
    *,
    now: datetime,
    retention_days: StreamRetentionDays,
) -> bool:
    keep_days = retention_days.for_stream(parsed.stream)
    cutoff = now - timedelta(days=keep_days)
    return parsed.date_start() < cutoff


def _merge_summary(left: MaintenanceSummary, right: MaintenanceSummary) -> MaintenanceSummary:
    return MaintenanceSummary(
        compressed_files=left.compressed_files + right.compressed_files,
        deleted_files=left.deleted_files + right.deleted_files,
        skipped_files=left.skipped_files + right.skipped_files,
    )
