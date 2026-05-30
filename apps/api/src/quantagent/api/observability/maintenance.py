from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import gzip
import os
from pathlib import Path
import shutil
import threading
from threading import Thread
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
        self._enabled = config.max_total_bytes is not None or config.min_free_bytes is not None
        self._lock = threading.Lock()
        self._state = DiskGuardState(under_pressure=False, total_bytes=0, free_bytes=0)
        self._next_refresh_at = 0.0
        self._refresh_in_progress = False
        if self._enabled:
            self._state = _compute_disk_guard_state(self._config)
            self._next_refresh_at = monotonic() + self._check_interval_seconds

    def current_state(self, *, force: bool = False) -> DiskGuardState:
        if not self._enabled:
            return self._state
        if force:
            return self._refresh_state()
        now = monotonic()
        with self._lock:
            if now < self._next_refresh_at or self._refresh_in_progress:
                return self._state
            # access 日志会在请求完成路径查询 disk guard；过期后转成后台刷新，避免同步磁盘遍历阻塞热路径。
            self._refresh_in_progress = True
        Thread(target=self._refresh_state_async, name="quantagent-api-disk-guard", daemon=True).start()
        with self._lock:
            return self._state

    def _refresh_state(self) -> DiskGuardState:
        state = _compute_disk_guard_state(self._config)
        with self._lock:
            self._state = state
            self._next_refresh_at = monotonic() + self._check_interval_seconds
            self._refresh_in_progress = False
            return self._state

    def _refresh_state_async(self) -> None:
        try:
            self._refresh_state()
        except Exception:
            with self._lock:
                self._next_refresh_at = monotonic() + self._check_interval_seconds
                self._refresh_in_progress = False


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
        temp_compressed_path = compressed_path.with_suffix(compressed_path.suffix + ".tmp")
        try:
            if compressed_path.exists():
                # 已存在同名 gzip 时保留历史内容，再追加一个 gzip member，避免关闭的 jsonl 永久残留。
                with compressed_path.open("rb") as existing, temp_compressed_path.open("wb") as target:
                    shutil.copyfileobj(existing, target)
                gzip_mode = "ab"
            else:
                gzip_mode = "wb"

            with parsed.path.open("rb") as source, gzip.open(temp_compressed_path, gzip_mode) as target:
                shutil.copyfileobj(source, target)
            temp_compressed_path.replace(compressed_path)
            parsed.path.unlink(missing_ok=True)
            return MaintenanceSummary(compressed_files=1)
        except OSError:
            temp_compressed_path.unlink(missing_ok=True)
            return MaintenanceSummary(skipped_files=1)


def _compute_disk_guard_state(config: MaintenanceConfig) -> DiskGuardState:
    root_dir = config.root_dir
    # 请求路径会周期性查询 disk guard；未启用对应阈值时跳过昂贵的目录遍历和磁盘统计。
    total_bytes = 0
    if config.max_total_bytes is not None and root_dir.exists():
        for path in root_dir.rglob("*"):
            try:
                if path.is_file():
                    total_bytes += path.stat().st_size
            except OSError:
                continue

    free_bytes = 0
    free_bytes_available = False
    if config.min_free_bytes is not None:
        usage_root = root_dir if root_dir.exists() else root_dir.parent
        try:
            free_bytes = shutil.disk_usage(usage_root).free
            free_bytes_available = True
        except OSError:
            free_bytes = 0

    reason: str | None = None
    under_pressure = False
    if config.max_total_bytes is not None and total_bytes >= config.max_total_bytes:
        under_pressure = True
        reason = "max_total_bytes"
    if config.min_free_bytes is not None and free_bytes_available and free_bytes <= config.min_free_bytes:
        under_pressure = True
        reason = reason or "min_free_bytes"
    return DiskGuardState(
        under_pressure=under_pressure,
        total_bytes=total_bytes,
        free_bytes=free_bytes,
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
    age_seconds = _file_age_seconds(parsed.path, now=now)
    if age_seconds is None:
        return False
    if parsed.date_slice == now.strftime("%Y%m%d"):
        # 同一天文件默认视为“可能仍在写入中”；但旧 pid 已消失时，说明该文件已不可能再被当前宿主机进程继续写入。
        return parsed.pid != os.getpid() and not _is_pid_running(parsed.pid)
    return age_seconds >= min_age_seconds


def _file_age_seconds(path: Path, *, now: datetime) -> float | None:
    try:
        return max(0.0, (now - datetime.fromtimestamp(path.stat().st_mtime, UTC)).total_seconds())
    except OSError:
        return None


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


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
