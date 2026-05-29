from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import socket
import threading
from time import perf_counter
from typing import Any

from fastapi import Request

from quantagent.api.config.settings import Settings
from quantagent.api.observability import events
from quantagent.api.observability.files import FileLayoutConfig, StreamFileWriterSet
from quantagent.api.observability.filters import ContextInjectionFilter, SensitiveDataRedactionFilter
from quantagent.api.observability.formatters import JsonLinesFormatter
from quantagent.api.observability.queue import QueueWriterRuntime


_LOGGER_NAME = "quantagent.api"
_SECURITY_LOGGED_FLAG = "_structured_security_logged"
_ERROR_LOGGED_EVENTS = "_structured_error_logged_events"
_RUNTIME_LOCK = threading.Lock()
_ACTIVE_RUNTIME: "_LoggingRuntime | None" = None


@dataclass(frozen=True)
class LoggingConfig:
    service: str
    env: str
    instance_id: str
    log_dir: Path
    log_level: str
    rotate_max_bytes: int
    queue_max_size: int
    access_drop_when_full: bool
    shutdown_timeout_seconds: float
    use_memory_sink: bool


class QueueStructuredFileHandler(logging.Handler):
    def __init__(self, runtime: QueueWriterRuntime, formatter: JsonLinesFormatter) -> None:
        super().__init__()
        self._runtime = runtime
        self.setFormatter(formatter)
        self.addFilter(ContextInjectionFilter())
        self.addFilter(SensitiveDataRedactionFilter())

    def emit(self, record: logging.LogRecord) -> None:
        line = self.format(record)
        stream = getattr(record, "stream", "app")
        self._runtime.enqueue(stream=stream, line=line, created_at=record.created)


class InMemoryStructuredHandler(logging.Handler):
    def __init__(self, formatter: JsonLinesFormatter) -> None:
        super().__init__()
        self.records: list[str] = []
        self.setFormatter(formatter)
        self.addFilter(ContextInjectionFilter())
        self.addFilter(SensitiveDataRedactionFilter())

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


@dataclass
class _LoggingRuntime:
    config: LoggingConfig
    queue_runtime: QueueWriterRuntime | None
    handler: logging.Handler

    def shutdown(self) -> None:
        if self.queue_runtime is not None:
            self.queue_runtime.stop()
        logger = logging.getLogger(_LOGGER_NAME)
        if self.handler in logger.handlers:
            logger.removeHandler(self.handler)
        uvicorn_error = logging.getLogger("uvicorn.error")
        if self.handler in uvicorn_error.handlers:
            uvicorn_error.removeHandler(self.handler)


def _build_config(settings: Settings) -> LoggingConfig:
    instance_id = settings.LOG_INSTANCE_ID or socket.gethostname() or "api-local"
    return LoggingConfig(
        service="api",
        env=settings.APP_ENV.lower(),
        instance_id=instance_id,
        log_dir=settings.LOG_DIR,
        log_level=settings.LOG_LEVEL.upper(),
        rotate_max_bytes=settings.LOG_ROTATE_MAX_BYTES,
        queue_max_size=settings.LOG_QUEUE_MAX_SIZE,
        access_drop_when_full=settings.LOG_ACCESS_DROP_WHEN_FULL,
        shutdown_timeout_seconds=settings.LOG_SHUTDOWN_DRAIN_TIMEOUT_SECONDS,
        use_memory_sink=settings.LOG_USE_MEMORY_SINK,
    )


def configure_api_logging(settings: Settings) -> None:
    global _ACTIVE_RUNTIME
    config = _build_config(settings)
    with _RUNTIME_LOCK:
        if _ACTIVE_RUNTIME is not None and _ACTIVE_RUNTIME.config == config:
            return
        if _ACTIVE_RUNTIME is not None:
            _ACTIVE_RUNTIME.shutdown()

        formatter = JsonLinesFormatter(
            service=config.service,
            env=config.env,
            instance_id=config.instance_id,
            pid=os.getpid(),
        )
        if config.use_memory_sink:
            queue_runtime = None
            handler: logging.Handler = InMemoryStructuredHandler(formatter)
        else:
            config.log_dir.mkdir(parents=True, exist_ok=True)
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=config.log_dir,
                    service=config.service,
                    env=config.env,
                    instance_id=config.instance_id,
                    pid=os.getpid(),
                    rotate_max_bytes=config.rotate_max_bytes,
                )
            )
            queue_runtime = QueueWriterRuntime(
                writer_set=writer_set,
                max_size=config.queue_max_size,
                access_drop_when_full=config.access_drop_when_full,
                shutdown_timeout_seconds=config.shutdown_timeout_seconds,
            )
            handler = QueueStructuredFileHandler(queue_runtime, formatter)
            queue_runtime.start()

        logger = logging.getLogger(_LOGGER_NAME)
        logger.handlers = [existing for existing in logger.handlers if not isinstance(existing, QueueStructuredFileHandler)]
        logger.setLevel(config.log_level)
        logger.propagate = False
        logger.addHandler(handler)

        uvicorn_error = logging.getLogger("uvicorn.error")
        uvicorn_error.handlers = [existing for existing in uvicorn_error.handlers if not isinstance(existing, QueueStructuredFileHandler)]
        uvicorn_error.setLevel(config.log_level)
        uvicorn_error.propagate = False
        uvicorn_error.addHandler(handler)

        uvicorn_access = logging.getLogger("uvicorn.access")
        uvicorn_access.handlers.clear()
        uvicorn_access.propagate = False
        uvicorn_access.disabled = True

        _ACTIVE_RUNTIME = _LoggingRuntime(config=config, queue_runtime=queue_runtime, handler=handler)

    log_structured(
        logging.INFO,
        event=events.LOGGING_CONFIGURED,
        stream="app",
        log_dir=str(config.log_dir),
        queue_max_size=config.queue_max_size,
        rotate_max_bytes=config.rotate_max_bytes,
    )


def shutdown_api_logging() -> None:
    global _ACTIVE_RUNTIME
    with _RUNTIME_LOCK:
        if _ACTIVE_RUNTIME is None:
            return
        runtime = _ACTIVE_RUNTIME
        _ACTIVE_RUNTIME = None
    runtime.shutdown()


def log_structured(level: int, *, event: str, stream: str, message: str | None = None, **fields: Any) -> None:
    logging.getLogger(_LOGGER_NAME).log(
        level,
        message or event,
        extra={"event": event, "stream": stream, "structured_data": fields},
    )


def log_access_event(request: Request, *, status_code: int, duration_ms: float) -> None:
    log_structured(
        logging.INFO,
        event=events.HTTP_REQUEST_COMPLETED,
        stream="access",
        status_code=status_code,
        duration_ms=round(duration_ms, 3),
        method=request.method,
        path=request.url.path,
        route=getattr(request.scope.get("route"), "path", None),
    )


def log_error_event(
    request: Request | None,
    *,
    event: str,
    component: str,
    failure_type: str,
    exception_type: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    if request is not None:
        logged_events = getattr(request.state, _ERROR_LOGGED_EVENTS, None)
        if not isinstance(logged_events, set):
            logged_events = set()
            setattr(request.state, _ERROR_LOGGED_EVENTS, logged_events)
        if event in logged_events:
            return
        logged_events.add(event)
    payload: dict[str, Any] = {
        "component": component,
        "failure_type": failure_type,
    }
    if exception_type:
        payload["exception_type"] = exception_type
    if details:
        payload["details"] = details
    log_structured(logging.ERROR, event=event, stream="error", **payload)


def log_security_event(
    request: Request | None,
    *,
    event: str,
    failure_type: str,
    details: dict[str, Any] | None = None,
) -> None:
    if request is not None and getattr(request.state, _SECURITY_LOGGED_FLAG, False):
        return
    if request is not None:
        setattr(request.state, _SECURITY_LOGGED_FLAG, True)
    payload: dict[str, Any] = {"failure_type": failure_type}
    if details:
        payload["details"] = details
    log_structured(logging.WARNING, event=event, stream="security", **payload)


def log_audit_event(*, event: str, action: str, actor_id: str, actor_type: str, request_id: str, path: str, method: str) -> None:
    log_structured(
        logging.INFO,
        event=event,
        stream="audit",
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        request_id=request_id,
        path=path,
        method=method,
    )


class RequestTiming:
    def __init__(self) -> None:
        self._started = perf_counter()

    def duration_ms(self) -> float:
        return (perf_counter() - self._started) * 1000.0
