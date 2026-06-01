from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Full, Queue
import sys
import threading
from pathlib import Path

from quantagent.api.observability.files import StreamFileWriterSet
from quantagent.api.observability.maintenance import DiskGuard


_STOP_STREAM = "__stop__"
_QUEUE_POLL_TIMEOUT_SECONDS = 0.05


@dataclass(frozen=True)
class QueuedLogLine:
    stream: str
    line: str
    created_at: float


class QueueWriterRuntime:
    def __init__(
        self,
        *,
        writer_set: StreamFileWriterSet,
        max_size: int,
        access_drop_when_full: bool,
        shutdown_timeout_seconds: float,
        disk_guard: DiskGuard | None = None,
    ) -> None:
        self._writer_set = writer_set
        self._queue: Queue[QueuedLogLine] = Queue(maxsize=max_size)
        self._access_drop_when_full = access_drop_when_full
        self._shutdown_timeout_seconds = shutdown_timeout_seconds
        self._disk_guard = disk_guard
        self._stop_requested = threading.Event()
        self._thread = threading.Thread(target=self._run, name="quantagent-api-log-writer", daemon=True)
        self._warning_lock = threading.Lock()
        self._warned_messages: set[str] = set()
        self._dropped_access_records = 0
        self._closed_paths: set[Path] = set()

    @property
    def dropped_access_records(self) -> int:
        return self._dropped_access_records

    @property
    def thread(self) -> threading.Thread:
        return self._thread

    def active_paths(self) -> set[Path]:
        return self._writer_set.active_paths()

    def closed_paths(self) -> set[Path]:
        writer_closed_paths = self._writer_set.closed_paths() if hasattr(self._writer_set, "closed_paths") else set()
        return writer_closed_paths | set(self._closed_paths)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def enqueue(self, *, stream: str, line: str, created_at: float) -> bool:
        if self._should_drop_access_for_disk_guard(stream):
            self._dropped_access_records += 1
            return False
        try:
            self._queue.put_nowait(QueuedLogLine(stream=stream, line=line, created_at=created_at))
            return True
        except Full:
            if stream == "access" and self._access_drop_when_full:
                self._dropped_access_records += 1
                self.warn_once("access-queue-full", "structured logging queue full; access log dropped")
                return False

            try:
                # 关键 stream 允许退化成受限直写，避免静默丢失错误和安全事件。
                self._writer_set.write(stream=stream, line=line, created_at=created_at)
                self.warn_once("critical-fallback", "structured logging queue full; critical stream used bounded fallback")
                return False
            except Exception:
                self.warn_once("critical-fallback-failed", "structured logging fallback write failed")
                return False

    def stop(self) -> bool:
        self._stop_requested.set()
        if self._thread.ident is None:
            self._drain_remaining()
            self._closed_paths.update(self._writer_set.close())
            return True
        # 用 sentinel 主动唤醒 listener，避免测试关闭 app 时为轮询超时白等。
        try:
            self._queue.put_nowait(QueuedLogLine(stream=_STOP_STREAM, line="", created_at=0.0))
        except Full:
            pass
        self._thread.join(timeout=self._shutdown_timeout_seconds)
        if self._thread.is_alive():
            self.warn_once("shutdown-timeout", "structured logging shutdown timed out before queue drained")
            return False
        return True

    def warn_once(self, key: str, message: str) -> None:
        with self._warning_lock:
            if key in self._warned_messages:
                return
            self._warned_messages.add(key)
        print(message, file=sys.stderr)

    def _should_drop_access_for_disk_guard(self, stream: str) -> bool:
        if stream != "access" or not self._access_drop_when_full or self._disk_guard is None:
            return False
        state = self._disk_guard.current_state()
        if not state.under_pressure:
            return False
        reason = state.reason or "unknown"
        self.warn_once(
            f"disk-guard-{reason}",
            "structured logging disk guard active; access log dropped",
        )
        return True

    def _drain_remaining(self) -> None:
        while True:
            try:
                queued = self._queue.get_nowait()
            except Empty:
                return
            try:
                if queued.stream == _STOP_STREAM:
                    continue
                self._write_queued_line(queued)
            finally:
                self._queue.task_done()

    def _write_queued_line(self, queued: QueuedLogLine) -> None:
        try:
            self._writer_set.write(stream=queued.stream, line=queued.line, created_at=queued.created_at)
        except Exception:
            self.warn_once("writer-error", "structured logging writer failed; record dropped")

    def _run(self) -> None:
        try:
            while True:
                if self._stop_requested.is_set() and self._queue.empty():
                    return
                try:
                    queued = self._queue.get(timeout=_QUEUE_POLL_TIMEOUT_SECONDS)
                except Empty:
                    continue

                try:
                    # sentinel 只负责唤醒 listener；真正退出取决于 stop 事件和队列 drain 完成。
                    if queued.stream != _STOP_STREAM:
                        self._write_queued_line(queued)
                finally:
                    self._queue.task_done()
        finally:
            self._closed_paths.update(self._writer_set.close())
