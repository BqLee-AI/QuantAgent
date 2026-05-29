from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Full, Queue
import sys
import threading

from quantagent.api.observability.files import StreamFileWriterSet


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
    ) -> None:
        self._writer_set = writer_set
        self._queue: Queue[QueuedLogLine] = Queue(maxsize=max_size)
        self._access_drop_when_full = access_drop_when_full
        self._shutdown_timeout_seconds = shutdown_timeout_seconds
        self._stop_requested = threading.Event()
        self._thread = threading.Thread(target=self._run, name="quantagent-api-log-writer", daemon=True)
        self._warning_lock = threading.Lock()
        self._warned_messages: set[str] = set()
        self._dropped_access_records = 0

    @property
    def dropped_access_records(self) -> int:
        return self._dropped_access_records

    @property
    def thread(self) -> threading.Thread:
        return self._thread

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def enqueue(self, *, stream: str, line: str, created_at: float) -> bool:
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

    def stop(self) -> None:
        self._stop_requested.set()
        if self._thread.ident is None:
            self._drain_remaining()
            self._writer_set.close()
            return
        # 用 sentinel 主动唤醒 listener，避免测试关闭 app 时为轮询超时白等。
        try:
            self._queue.put_nowait(QueuedLogLine(stream=_STOP_STREAM, line="", created_at=0.0))
        except Full:
            pass
        self._thread.join(timeout=self._shutdown_timeout_seconds)
        if self._thread.is_alive():
            self.warn_once("shutdown-timeout", "structured logging shutdown timed out before queue drained")
            return
        if self._thread.ident is None:
            self._drain_remaining()
            self._writer_set.close()

    def warn_once(self, key: str, message: str) -> None:
        with self._warning_lock:
            if key in self._warned_messages:
                return
            self._warned_messages.add(key)
        print(message, file=sys.stderr)

    def _drain_remaining(self) -> None:
        while True:
            try:
                queued = self._queue.get_nowait()
            except Empty:
                return
            if queued.stream == _STOP_STREAM:
                self._queue.task_done()
                continue
            self._writer_set.write(stream=queued.stream, line=queued.line, created_at=queued.created_at)
            self._queue.task_done()

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
                        self._writer_set.write(stream=queued.stream, line=queued.line, created_at=queued.created_at)
                finally:
                    self._queue.task_done()
        finally:
            self._writer_set.close()
