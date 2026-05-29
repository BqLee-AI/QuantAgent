from __future__ import annotations

import io
import json
import logging
from types import SimpleNamespace
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from quantagent.api.observability.context import clear_request_context, set_actor_context, set_request_context
from quantagent.api.observability.files import (
    FileLayoutConfig,
    StreamFileWriterSet,
    build_stream_directory,
    build_stream_filename,
)
from quantagent.api.observability.filters import ContextInjectionFilter, SensitiveDataRedactionFilter, redact_value
from quantagent.api.observability.formatters import JsonLinesFormatter
from quantagent.api.observability.logging import log_error_event
from quantagent.api.observability.queue import QueueWriterRuntime


class ObservabilityTestCase(unittest.TestCase):
    def test_jsonl_formatter_includes_stable_fields_and_context(self) -> None:
        formatter = JsonLinesFormatter(service="api", env="test", instance_id="api-test", pid=123)
        record = logging.LogRecord("quantagent.api", logging.INFO, __file__, 10, "hello", (), None)
        record.stream = "access"
        record.event = "http.request.completed"
        record.structured_data = {"request_id": "req-1", "trace_id": "trace-1", "path": "/health", "status_code": 200}

        payload = json.loads(formatter.format(record))

        self.assertEqual(payload["service"], "api")
        self.assertEqual(payload["env"], "test")
        self.assertEqual(payload["instance_id"], "api-test")
        self.assertEqual(payload["pid"], 123)
        self.assertEqual(payload["stream"], "access")
        self.assertEqual(payload["event"], "http.request.completed")
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["trace_id"], "trace-1")
        self.assertEqual(payload["path"], "/health")
        self.assertEqual(payload["status_code"], 200)

    def test_jsonl_formatter_keeps_reserved_fields_authoritative(self) -> None:
        formatter = JsonLinesFormatter(service="api", env="test", instance_id="api-test", pid=123)
        record = logging.LogRecord("quantagent.api", logging.INFO, __file__, 10, "hello", (), None)
        record.stream = "access"
        record.event = "http.request.completed"
        record.structured_data = {
            "service": "spoofed",
            "event": "spoofed.event",
            "pid": 999,
            "request_id": "req-1",
            "status_code": 200,
        }

        payload = json.loads(formatter.format(record))

        self.assertEqual(payload["service"], "api")
        self.assertEqual(payload["event"], "http.request.completed")
        self.assertEqual(payload["pid"], 123)
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["status_code"], 200)

    def test_context_and_redaction_filters_mask_sensitive_fields(self) -> None:
        token = set_request_context(request_id="req-ctx", trace_id="trace-ctx", method="POST", path="/api/v1/auth/login")
        try:
            set_actor_context(actor_type="local_single_user", actor_id="actor-1")
            record = logging.LogRecord("quantagent.api", logging.WARNING, __file__, 10, "db=postgresql://user:pass@db/app", (), None)
            record.stream = "security"
            record.structured_data = {
                "authorization": "Bearer secret",
                "cookie": "session=abc",
                "database_url": "postgresql://user:pass@db/app",
            }

            self.assertTrue(ContextInjectionFilter().filter(record))
            self.assertTrue(SensitiveDataRedactionFilter().filter(record))

            self.assertEqual(record.structured_data["authorization"], "[REDACTED]")
            self.assertEqual(record.structured_data["cookie"], "[REDACTED]")
            self.assertEqual(record.structured_data["database_url"], "[REDACTED]")
            self.assertEqual(record.structured_data["request_id"], "req-ctx")
            self.assertEqual(record.structured_data["trace_id"], "trace-ctx")
            self.assertEqual(record.structured_data["actor_id"], "actor-1")
            self.assertEqual(record.msg, "db=[REDACTED]")
        finally:
            clear_request_context(token)

    def test_redact_value_masks_nested_sensitive_fields(self) -> None:
        payload = redact_value(
            "details",
            {
                "password": "secret",
                "headers": {"x-csrf-token": "csrf", "other": "ok"},
                "items": ["postgresql://user:pass@db/app"],
            },
        )
        self.assertEqual(payload["password"], "[REDACTED]")
        self.assertEqual(payload["headers"]["x-csrf-token"], "[REDACTED]")
        self.assertEqual(payload["items"][0], "[REDACTED]")

    def test_log_error_event_deduplicates_per_event(self) -> None:
        request = SimpleNamespace(state=SimpleNamespace())
        events: list[str] = []

        with patch("quantagent.api.observability.logging.log_structured") as log_structured_mock:
            log_structured_mock.side_effect = lambda _level, *, event, stream, **_fields: events.append(event)
            log_error_event(request, event="db.session.missing", component="database", failure_type="missing")
            log_error_event(request, event="db.session.missing", component="database", failure_type="missing")
            log_error_event(request, event="http.unhandled", component="http", failure_type="unhandled")

        self.assertEqual(events, ["db.session.missing", "http.unhandled"])

    def test_file_layout_and_naming_use_stream_date_pid_and_hour(self) -> None:
        timestamp = time.gmtime(1714554000)
        dt = time.strftime("%Y-%m-%dT%H:%M:%S", timestamp)
        from datetime import datetime, UTC

        current = datetime(2024, 5, 1, 9, 0, 0, tzinfo=UTC)
        directory = build_stream_directory(Path("/tmp/logs"), "access", current)
        filename = build_stream_filename(
            service="api",
            env="test",
            instance_id="api-test",
            pid=321,
            stream="access",
            timestamp=current,
            part=2,
        )

        self.assertEqual(str(directory), "/tmp/logs/access/2024/05/01")
        self.assertEqual(filename, "api.test.api-test.pid-321.access.20240501T09.part-002.jsonl")
        self.assertTrue(dt)

    def test_file_writer_rotates_by_size_and_hour(self) -> None:
        from datetime import datetime, UTC

        with tempfile.TemporaryDirectory() as tmp_dir:
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=Path(tmp_dir),
                    service="api",
                    env="test",
                    instance_id="api-test",
                    pid=123,
                    rotate_max_bytes=32,
                )
            )
            first_path = writer_set.write(
                stream="access",
                line='{"event":"a"}',
                created_at=datetime(2024, 5, 1, 9, 0, 0, tzinfo=UTC).timestamp(),
            )
            second_path = writer_set.write(
                stream="access",
                line='{"event":"this-is-large-enough-to-rotate"}',
                created_at=datetime(2024, 5, 1, 9, 1, 0, tzinfo=UTC).timestamp(),
            )
            third_path = writer_set.write(
                stream="access",
                line='{"event":"b"}',
                created_at=datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC).timestamp(),
            )
            writer_set.close()

        self.assertIn(".access.20240501T09.jsonl", first_path.name)
        self.assertIn(".access.20240501T09.part-001.jsonl", second_path.name)
        self.assertIn(".access.20240501T10.jsonl", third_path.name)

    def test_queue_full_drops_access_and_fallback_writes_error(self) -> None:
        class BlockingWriterSet:
            def __init__(self) -> None:
                self.writes: list[tuple[str, str]] = []
                self.release = threading.Event()

            def write(self, *, stream: str, line: str, created_at: float):
                self.release.wait(timeout=1.0)
                self.writes.append((stream, line))
                return Path("/tmp/fake.jsonl")

            def close(self) -> None:
                return None

        writer_set = BlockingWriterSet()
        with patch("sys.stderr", new_callable=io.StringIO):
            runtime = QueueWriterRuntime(
                writer_set=writer_set,  # type: ignore[arg-type]
                max_size=1,
                access_drop_when_full=True,
                shutdown_timeout_seconds=0.5,
            )
            runtime.start()

            self.assertTrue(runtime.enqueue(stream="access", line='{"event":"first"}', created_at=time.time()))
            # 等待 worker 抢走第一条并阻塞写入，然后再塞一条占满队列。
            time.sleep(0.05)
            self.assertTrue(runtime.enqueue(stream="access", line='{"event":"queued"}', created_at=time.time()))
            dropped = runtime.enqueue(stream="access", line='{"event":"second"}', created_at=time.time())
            self.assertFalse(dropped)
            self.assertGreaterEqual(runtime.dropped_access_records, 1)

            error_result = runtime.enqueue(stream="error", line='{"event":"error"}', created_at=time.time())
            self.assertFalse(error_result)

            writer_set.release.set()
            runtime.stop()
        self.assertTrue(any(stream == "error" for stream, _line in writer_set.writes))

    def test_queue_full_drops_access_and_fallback_writes_error_to_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=Path(tmp_dir),
                    service="api",
                    env="test",
                    instance_id="api-test",
                    pid=555,
                    rotate_max_bytes=1024,
                )
            )
            with patch("sys.stderr", new_callable=io.StringIO):
                runtime = QueueWriterRuntime(
                    writer_set=writer_set,
                    max_size=1,
                    access_drop_when_full=True,
                    shutdown_timeout_seconds=0.5,
                )
                runtime.start()

                self.assertTrue(runtime.enqueue(stream="access", line='{"event":"first"}', created_at=time.time()))
                dropped = runtime.enqueue(stream="access", line='{"event":"second"}', created_at=time.time())
                self.assertFalse(dropped)
                self.assertGreaterEqual(runtime.dropped_access_records, 1)

                runtime.stop()
            access_dir = Path(tmp_dir) / "access"
            self.assertTrue(access_dir.exists())

    def test_queue_shutdown_stops_listener_and_flushes_enqueued_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=Path(tmp_dir),
                    service="api",
                    env="test",
                    instance_id="api-test",
                    pid=999,
                    rotate_max_bytes=1024,
                )
            )
            with patch("sys.stderr", new_callable=io.StringIO):
                runtime = QueueWriterRuntime(
                    writer_set=writer_set,
                    max_size=16,
                    access_drop_when_full=True,
                    shutdown_timeout_seconds=1.0,
                )
                runtime.start()
                runtime.enqueue(stream="audit", line='{"event":"audit"}', created_at=time.time())
                runtime.stop()

            self.assertFalse(runtime.thread.is_alive())
            written_files = list(Path(tmp_dir).rglob("*.jsonl"))
            self.assertTrue(written_files)
            contents = written_files[0].read_text(encoding="utf-8")
            self.assertIn('"event":"audit"', contents)

    def test_queue_shutdown_eventually_stops_when_sentinel_cannot_be_enqueued(self) -> None:
        class BlockingWriterSet:
            def __init__(self) -> None:
                self.writes: list[tuple[str, str]] = []
                self.started_write = threading.Event()
                self.release = threading.Event()
                self.closed = threading.Event()

            def write(self, *, stream: str, line: str, created_at: float):
                self.started_write.set()
                self.release.wait(timeout=2.0)
                self.writes.append((stream, line))
                return Path("/tmp/fake.jsonl")

            def close(self) -> None:
                self.closed.set()

        writer_set = BlockingWriterSet()
        with patch("sys.stderr", new_callable=io.StringIO):
            runtime = QueueWriterRuntime(
                writer_set=writer_set,  # type: ignore[arg-type]
                max_size=1,
                access_drop_when_full=True,
                shutdown_timeout_seconds=0.1,
            )
            runtime.start()
            self.assertTrue(runtime.enqueue(stream="app", line='{"event":"first"}', created_at=time.time()))
            self.assertTrue(writer_set.started_write.wait(timeout=1.0))
            self.assertTrue(runtime.enqueue(stream="app", line='{"event":"queued"}', created_at=time.time()))

            runtime.stop()
            self.assertTrue(runtime.thread.is_alive())

            writer_set.release.set()
            runtime.thread.join(timeout=1.0)

        self.assertFalse(runtime.thread.is_alive())
        self.assertTrue(writer_set.closed.is_set())
        self.assertEqual(writer_set.writes, [("app", '{"event":"first"}'), ("app", '{"event":"queued"}')])

    def test_queue_writer_error_drops_record_and_continues(self) -> None:
        class FlakyWriterSet:
            def __init__(self) -> None:
                self.writes: list[tuple[str, str]] = []
                self.closed = False
                self.fail_next = True

            def write(self, *, stream: str, line: str, created_at: float):
                if self.fail_next:
                    self.fail_next = False
                    raise OSError("disk unavailable")
                self.writes.append((stream, line))
                return Path("/tmp/fake.jsonl")

            def close(self) -> None:
                self.closed = True

        writer_set = FlakyWriterSet()
        with patch("sys.stderr", new_callable=io.StringIO):
            runtime = QueueWriterRuntime(
                writer_set=writer_set,  # type: ignore[arg-type]
                max_size=16,
                access_drop_when_full=True,
                shutdown_timeout_seconds=1.0,
            )
            runtime.start()
            runtime.enqueue(stream="app", line='{"event":"first"}', created_at=time.time())
            runtime.enqueue(stream="app", line='{"event":"second"}', created_at=time.time())
            runtime.stop()

        self.assertFalse(runtime.thread.is_alive())
        self.assertTrue(writer_set.closed)
        self.assertEqual(writer_set.writes, [("app", '{"event":"second"}')])

    def test_test_settings_use_memory_sink_by_default(self) -> None:
        from quantagent.api.config.settings import Settings

        settings = Settings(
            _env_file=None,
            APP_ENV="test",
            DATABASE_URL=None,
            RUNTIME_DIR="runtime",
            LOG_LEVEL="INFO",
            AUTH_ENABLED=False,
        )
        self.assertTrue(settings.LOG_USE_MEMORY_SINK)


if __name__ == "__main__":
    unittest.main()
