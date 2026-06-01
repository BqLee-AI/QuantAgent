from __future__ import annotations

import gzip
import io
import json
import logging
import os
import shutil
from threading import Event
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
    parse_log_file,
)
from quantagent.api.observability.filters import ContextInjectionFilter, SensitiveDataRedactionFilter, redact_value
from quantagent.api.observability.formatters import JsonLinesFormatter
from quantagent.api.observability.logging import (
    _LoggingRuntime,
    InMemoryStructuredHandler,
    QueueStructuredFileHandler,
    configure_api_logging,
    log_error_event,
    shutdown_api_logging,
)
from quantagent.api.observability.maintenance import (
    DiskGuard,
    DiskGuardState,
    LogMaintenanceRuntime,
    MaintenanceConfig,
    StreamRetentionDays,
    _compute_disk_guard_state,
)
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

    def test_jsonl_formatter_redacts_rendered_message_without_mutating_record(self) -> None:
        formatter = JsonLinesFormatter(service="api", env="test", instance_id="api-test", pid=123)
        record = logging.LogRecord(
            "quantagent.api",
            logging.WARNING,
            __file__,
            10,
            "db=%s",
            ("postgresql://user:pass@db/app",),
            None,
        )

        payload = json.loads(formatter.format(record))

        self.assertEqual(payload["message"], "db=[REDACTED]")
        self.assertEqual(record.msg, "db=%s")
        self.assertEqual(record.args, ("postgresql://user:pass@db/app",))

    def test_jsonl_formatter_serializes_non_json_structured_values_safely(self) -> None:
        formatter = JsonLinesFormatter(service="api", env="test", instance_id="api-test", pid=123)
        record = logging.LogRecord("quantagent.api", logging.ERROR, __file__, 10, "failed", (), None)
        record.structured_data = {
            "details": {
                "path": Path("/tmp/runtime/object"),
                "items": {1, 2},
                "database_url": "postgresql://user:pass@db/app",
            }
        }

        payload = json.loads(formatter.format(record))

        self.assertEqual(payload["details"]["path"], "/tmp/runtime/object")
        self.assertEqual(sorted(payload["details"]["items"]), [1, 2])
        self.assertEqual(payload["details"]["database_url"], "[REDACTED]")

    def test_jsonl_formatter_supports_uvicorn_ipv6_percent_style_message(self) -> None:
        formatter = JsonLinesFormatter(service="api", env="test", instance_id="api-test", pid=123)
        record = logging.LogRecord(
            "uvicorn.error",
            logging.INFO,
            __file__,
            10,
            "Uvicorn running on %s://[%s]:%d (Press CTRL+C to quit)",
            ("http", "::1", 8000),
            None,
        )

        payload = json.loads(formatter.format(record))

        self.assertEqual(payload["logger"], "uvicorn.error")
        self.assertEqual(payload["message"], "Uvicorn running on [REDACTED] (Press CTRL+C to quit)")

    def test_structured_handler_does_not_mutate_uvicorn_console_record(self) -> None:
        formatter = JsonLinesFormatter(service="api", env="test", instance_id="api-test", pid=123)
        handler = InMemoryStructuredHandler(formatter)
        record = logging.LogRecord(
            "uvicorn.error",
            logging.INFO,
            __file__,
            10,
            "Uvicorn running on %s://%s:%d (Press CTRL+C to quit)",
            ("http", "127.0.0.1", 8000),
            None,
        )
        record.color_message = "Uvicorn running on %s://%s:%d (Press CTRL+C to quit)"

        handler.emit(record)

        self.assertEqual(record.color_message, "Uvicorn running on %s://%s:%d (Press CTRL+C to quit)")
        self.assertEqual(record.getMessage(), "Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)")
        payload = json.loads(handler.records[0])
        self.assertEqual(payload["message"], "Uvicorn running on [REDACTED] (Press CTRL+C to quit)")

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
            self.assertEqual(record.msg, "db=postgresql://user:pass@db/app")
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

    def test_file_layout_and_naming_use_stream_date_pid_and_day(self) -> None:
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
        self.assertEqual(filename, "api.test.api-test.pid-321.access.20240501.part-002.jsonl")
        self.assertTrue(dt)

    def test_parse_log_file_supports_jsonl_and_gzip(self) -> None:
        parsed = parse_log_file(Path("api.test.api-test.pid-321.access.20240501.part-002.jsonl"))
        compressed = parse_log_file(Path("api.test.api-test.pid-321.access.20240501.jsonl.gz"))

        assert parsed is not None
        assert compressed is not None
        self.assertEqual(parsed.stream, "access")
        self.assertEqual(parsed.part, 2)
        self.assertFalse(parsed.compressed)
        self.assertEqual(compressed.stream, "access")
        self.assertEqual(compressed.part, 0)
        self.assertTrue(compressed.compressed)

    def test_file_writer_rotates_by_size_and_day(self) -> None:
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

        self.assertIn(".access.20240501.jsonl", first_path.name)
        self.assertIn(".access.20240501.part-001.jsonl", second_path.name)
        self.assertIn(".access.20240501.part-002.jsonl", third_path.name)

    def test_file_writer_rotates_to_new_file_when_date_changes(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=Path(tmp_dir),
                    service="api",
                    env="test",
                    instance_id="api-test",
                    pid=123,
                    rotate_max_bytes=4096,
                )
            )
            first_path = writer_set.write(
                stream="access",
                line='{"event":"a"}',
                created_at=datetime(2024, 5, 1, 23, 59, 0, tzinfo=UTC).timestamp(),
            )
            second_path = writer_set.write(
                stream="access",
                line='{"event":"b"}',
                created_at=datetime(2024, 5, 2, 0, 0, 1, tzinfo=UTC).timestamp(),
            )
            writer_set.close()

        self.assertIn(".access.20240501.jsonl", first_path.name)
        self.assertIn(".access.20240502.jsonl", second_path.name)

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

    def test_queue_disk_guard_drops_access_before_critical_streams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pressure_file = Path(tmp_dir) / "pressure.bin"
            pressure_file.write_bytes(b"disk-pressure")
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
            guard = DiskGuard(
                config=MaintenanceConfig(
                    root_dir=Path(tmp_dir),
                    min_age_seconds=1,
                    retention_days=StreamRetentionDays(access=1, app=1, error=1, security=1, audit=1),
                    max_total_bytes=1,
                    min_free_bytes=None,
                )
            )
            warning_buffer = io.StringIO()
            with patch("sys.stderr", new=warning_buffer):
                runtime = QueueWriterRuntime(
                    writer_set=writer_set,
                    max_size=16,
                    access_drop_when_full=True,
                    shutdown_timeout_seconds=1.0,
                    disk_guard=guard,
                )
                runtime.start()
                try:
                    self.assertFalse(runtime.enqueue(stream="access", line='{"event":"access"}', created_at=time.time()))
                    self.assertTrue(runtime.enqueue(stream="error", line='{"event":"error"}', created_at=time.time()))
                finally:
                    runtime.stop()

            self.assertIn("disk guard active", warning_buffer.getvalue())
            written_files = list(Path(tmp_dir).rglob("*.jsonl*"))
            self.assertTrue(written_files)
            contents = "\n".join(path.read_text(encoding="utf-8") for path in written_files if path.suffix == ".jsonl")
            self.assertIn('"event":"error"', contents)
            self.assertNotIn('"event":"access"', contents)

    def test_disk_guard_skips_unconfigured_expensive_checks(self) -> None:
        config = MaintenanceConfig(
            root_dir=Path("/tmp/unused"),
            min_age_seconds=1,
            retention_days=StreamRetentionDays(access=1, app=1, error=1, security=1, audit=1),
            max_total_bytes=None,
            min_free_bytes=None,
        )

        with patch("quantagent.api.observability.maintenance.shutil.disk_usage", side_effect=AssertionError("disk_usage should not run")):
            with patch.object(Path, "rglob", side_effect=AssertionError("rglob should not run")):
                state = _compute_disk_guard_state(config)

        self.assertFalse(state.under_pressure)
        self.assertEqual(state.total_bytes, 0)
        self.assertEqual(state.free_bytes, 0)

    def test_disk_guard_uses_only_threshold_specific_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            (root_dir / "a.log").write_text("1234", encoding="utf-8")
            retention_days = StreamRetentionDays(access=1, app=1, error=1, security=1, audit=1)

            with patch("quantagent.api.observability.maintenance.shutil.disk_usage", side_effect=AssertionError("disk_usage should not run")):
                total_only_state = _compute_disk_guard_state(
                    MaintenanceConfig(
                        root_dir=root_dir,
                        min_age_seconds=1,
                        retention_days=retention_days,
                        max_total_bytes=1,
                        min_free_bytes=None,
                    )
                )

            self.assertTrue(total_only_state.under_pressure)
            self.assertEqual(total_only_state.reason, "max_total_bytes")
            self.assertGreater(total_only_state.total_bytes, 0)
            self.assertEqual(total_only_state.free_bytes, 0)

            usage = shutil.disk_usage(root_dir)
            with patch.object(Path, "rglob", side_effect=AssertionError("rglob should not run")):
                with patch("quantagent.api.observability.maintenance.shutil.disk_usage", return_value=usage):
                    free_only_state = _compute_disk_guard_state(
                        MaintenanceConfig(
                            root_dir=root_dir,
                            min_age_seconds=1,
                            retention_days=retention_days,
                            max_total_bytes=None,
                            min_free_bytes=usage.free + 1,
                        )
                    )

            self.assertTrue(free_only_state.under_pressure)
            self.assertEqual(free_only_state.reason, "min_free_bytes")
            self.assertEqual(free_only_state.total_bytes, 0)
            self.assertEqual(free_only_state.free_bytes, usage.free)

    def test_disk_guard_ignores_stat_and_disk_usage_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            (root_dir / "a.log").write_text("1234", encoding="utf-8")
            retention_days = StreamRetentionDays(access=1, app=1, error=1, security=1, audit=1)

            original_is_file = Path.is_file
            original_stat = Path.stat

            def flaky_is_file(path: Path) -> bool:
                return path.name == "a.log" or original_is_file(path)

            def flaky_stat(path: Path, *args, **kwargs):
                if path.name == "a.log":
                    raise OSError("stat failed")
                return original_stat(path, *args, **kwargs)

            with patch.object(Path, "is_file", new=flaky_is_file):
                with patch.object(Path, "stat", new=flaky_stat):
                    with patch("quantagent.api.observability.maintenance.shutil.disk_usage", side_effect=OSError("disk usage failed")):
                        state = _compute_disk_guard_state(
                            MaintenanceConfig(
                                root_dir=root_dir,
                                min_age_seconds=1,
                                retention_days=retention_days,
                                max_total_bytes=1,
                                min_free_bytes=1,
                            )
                        )

            self.assertFalse(state.under_pressure)
            self.assertEqual(state.total_bytes, 0)
            self.assertEqual(state.free_bytes, 0)

    def test_disk_guard_returns_cached_state_while_async_refresh_runs(self) -> None:
        refresh_started = Event()
        release_refresh = Event()
        call_count = 0

        def mocked_compute(_config: MaintenanceConfig) -> DiskGuardState:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return DiskGuardState(under_pressure=False, total_bytes=0, free_bytes=0, reason=None)
            refresh_started.set()
            release_refresh.wait(timeout=1.0)
            return DiskGuardState(under_pressure=True, total_bytes=10, free_bytes=0, reason="max_total_bytes")

        with patch("quantagent.api.observability.maintenance._compute_disk_guard_state") as compute_mock:
            compute_mock.side_effect = mocked_compute
            guard = DiskGuard(
                config=MaintenanceConfig(
                    root_dir=Path("/tmp/unused"),
                    min_age_seconds=1,
                    retention_days=StreamRetentionDays(access=1, app=1, error=1, security=1, audit=1),
                    max_total_bytes=1,
                    min_free_bytes=None,
                ),
                check_interval_seconds=0.0,
            )

            cached = guard.current_state()
            self.assertFalse(cached.under_pressure)
            self.assertTrue(refresh_started.wait(timeout=1.0))
            second = guard.current_state()
            self.assertIs(second, cached)
            release_refresh.set()
            time.sleep(0.05)
            refreshed = guard.current_state(force=True)
            self.assertTrue(refreshed.under_pressure)

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

    def test_queue_stop_returns_false_when_listener_does_not_finish(self) -> None:
        class BlockingWriterSet:
            def __init__(self) -> None:
                self.started_write = threading.Event()
                self.release = threading.Event()

            def write(self, *, stream: str, line: str, created_at: float):
                self.started_write.set()
                self.release.wait(timeout=2.0)
                return Path("/tmp/fake.jsonl")

            def active_paths(self) -> set[Path]:
                return {Path("/tmp/fake.jsonl")}

            def close(self) -> None:
                return None

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

            try:
                self.assertFalse(runtime.stop())
                self.assertTrue(runtime.thread.is_alive())
            finally:
                writer_set.release.set()
                runtime.thread.join(timeout=1.0)

    def test_logging_shutdown_skips_shutdown_cleanup_when_queue_stop_times_out(self) -> None:
        class BlockingWriterSet:
            def __init__(self) -> None:
                self.started_write = threading.Event()
                self.release = threading.Event()

            def write(self, *, stream: str, line: str, created_at: float):
                self.started_write.set()
                self.release.wait(timeout=2.0)
                return Path("/tmp/fake.jsonl")

            def active_paths(self) -> set[Path]:
                return {Path("/tmp/fake.jsonl")}

            def close(self) -> None:
                return None

        class FakeMaintenanceRuntime:
            def __init__(self) -> None:
                self.calls: list[set[Path]] = []

            def run_shutdown_cleanup(self, *, force_closed_paths: set[Path]) -> None:
                self.calls.append(force_closed_paths)

        writer_set = BlockingWriterSet()
        maintenance_runtime = FakeMaintenanceRuntime()
        with patch("sys.stderr", new_callable=io.StringIO):
            queue_runtime = QueueWriterRuntime(
                writer_set=writer_set,  # type: ignore[arg-type]
                max_size=1,
                access_drop_when_full=True,
                shutdown_timeout_seconds=0.1,
            )
            queue_runtime.start()
            self.assertTrue(queue_runtime.enqueue(stream="app", line='{"event":"first"}', created_at=time.time()))
            self.assertTrue(writer_set.started_write.wait(timeout=1.0))

            runtime = _LoggingRuntime(
                config=None,  # type: ignore[arg-type]
                queue_runtime=queue_runtime,
                handler=logging.NullHandler(),
                maintenance_runtime=maintenance_runtime,  # type: ignore[arg-type]
            )
            try:
                runtime.shutdown()
                self.assertEqual(maintenance_runtime.calls, [])
            finally:
                writer_set.release.set()
                queue_runtime.thread.join(timeout=1.0)

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

    def test_configure_logging_keeps_uvicorn_error_console_propagation(self) -> None:
        from quantagent.api.config.settings import Settings

        shutdown_api_logging()
        uvicorn_error = logging.getLogger("uvicorn.error")
        before_handlers = list(uvicorn_error.handlers)
        before_propagate = uvicorn_error.propagate
        self.addCleanup(shutdown_api_logging)
        self.addCleanup(lambda: setattr(uvicorn_error, "handlers", before_handlers))
        self.addCleanup(lambda: setattr(uvicorn_error, "propagate", before_propagate))

        settings = Settings(
            _env_file=None,
            APP_ENV="local",
            DATABASE_URL=None,
            RUNTIME_DIR="runtime",
            LOG_LEVEL="INFO",
            LOG_USE_MEMORY_SINK=False,
            AUTH_ENABLED=False,
        )

        configure_api_logging(settings)

        self.assertTrue(uvicorn_error.propagate)
        self.assertTrue(any(isinstance(handler, QueueStructuredFileHandler) for handler in uvicorn_error.handlers))

    def test_maintenance_skips_active_or_unconfirmed_files_during_startup_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            active_path = root_dir / "access/2024/05/01/api.test.api-test.pid-321.access.20240501.jsonl"
            active_path.parent.mkdir(parents=True, exist_ok=True)
            active_path.write_text('{"event":"active"}\n', encoding="utf-8")
            now = time.time()
            os.utime(active_path, (now, now))
            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                from datetime import UTC, datetime

                fixed_now = datetime(2024, 5, 1, 9, 10, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                with patch("quantagent.api.observability.maintenance._is_pid_running", return_value=True):
                    runtime = LogMaintenanceRuntime(
                        MaintenanceConfig(
                            root_dir=root_dir,
                            min_age_seconds=300,
                            retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                            max_total_bytes=None,
                            min_free_bytes=None,
                        )
                    )
                    summary = runtime.run_startup_cleanup()

            self.assertEqual(summary.compressed_files, 0)
            self.assertEqual(summary.deleted_files, 0)
            self.assertGreaterEqual(summary.skipped_files, 1)
            self.assertTrue(active_path.exists())
            self.assertFalse(active_path.with_suffix(".jsonl.gz").exists())
            self.assertTrue(now > 0)

    def test_maintenance_compresses_closed_files_and_startup_compensates_previous_run(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            closed_path = root_dir / "error/2024/04/30/api.test.api-test.pid-321.error.20240430.part-001.jsonl"
            closed_path.parent.mkdir(parents=True, exist_ok=True)
            closed_path.write_text('{"event":"error"}\n', encoding="utf-8")
            old_mtime = datetime(2024, 4, 30, 8, 5, 0, tzinfo=UTC).timestamp()
            os.utime(closed_path, (old_mtime, old_mtime))

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                runtime = LogMaintenanceRuntime(
                    MaintenanceConfig(
                        root_dir=root_dir,
                        min_age_seconds=60,
                        retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                        max_total_bytes=None,
                        min_free_bytes=None,
                    )
                )
                summary = runtime.run_startup_cleanup()

            compressed_path = closed_path.with_suffix(".jsonl.gz")
            self.assertEqual(summary.compressed_files, 1)
            self.assertFalse(closed_path.exists())
            self.assertTrue(compressed_path.exists())

    def test_maintenance_startup_compresses_same_day_orphan_file_from_dead_pid(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            orphan_path = root_dir / "error/2024/05/01/api.test.api-test.pid-43210.error.20240501.jsonl"
            orphan_path.parent.mkdir(parents=True, exist_ok=True)
            orphan_path.write_text('{"event":"orphan"}\n', encoding="utf-8")
            old_mtime = datetime(2024, 5, 1, 8, 5, 0, tzinfo=UTC).timestamp()
            os.utime(orphan_path, (old_mtime, old_mtime))

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                with patch("quantagent.api.observability.maintenance._is_pid_running", return_value=False):
                    runtime = LogMaintenanceRuntime(
                        MaintenanceConfig(
                            root_dir=root_dir,
                            min_age_seconds=60,
                            retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                            max_total_bytes=None,
                            min_free_bytes=None,
                        )
                    )
                    summary = runtime.run_startup_cleanup()

            compressed_path = orphan_path.with_suffix(".jsonl.gz")
            self.assertEqual(summary.compressed_files, 1)
            self.assertFalse(orphan_path.exists())
            self.assertTrue(compressed_path.exists())

    def test_maintenance_startup_compresses_same_day_orphan_file_without_waiting_min_age(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            orphan_path = root_dir / "app/2024/05/01/api.test.api-test.pid-43210.app.20240501.jsonl"
            orphan_path.parent.mkdir(parents=True, exist_ok=True)
            orphan_path.write_text('{"event":"orphan"}\n', encoding="utf-8")
            recent_mtime = datetime(2024, 5, 1, 9, 59, 50, tzinfo=UTC).timestamp()
            os.utime(orphan_path, (recent_mtime, recent_mtime))

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                with patch("quantagent.api.observability.maintenance._is_pid_running", return_value=False):
                    runtime = LogMaintenanceRuntime(
                        MaintenanceConfig(
                            root_dir=root_dir,
                            min_age_seconds=300,
                            retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                            max_total_bytes=None,
                            min_free_bytes=None,
                        )
                    )
                    summary = runtime.run_startup_cleanup()

            compressed_path = orphan_path.with_suffix(".jsonl.gz")
            self.assertEqual(summary.compressed_files, 1)
            self.assertFalse(orphan_path.exists())
            self.assertTrue(compressed_path.exists())

    def test_maintenance_appends_closed_file_when_compressed_target_exists(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            closed_path = root_dir / "error/2024/04/30/api.test.api-test.pid-321.error.20240430.jsonl"
            compressed_path = closed_path.with_suffix(".jsonl.gz")
            closed_path.parent.mkdir(parents=True, exist_ok=True)
            closed_path.write_text('{"event":"new"}\n', encoding="utf-8")
            with gzip.open(compressed_path, "wt", encoding="utf-8") as compressed:
                compressed.write('{"event":"old"}\n')
            old_mtime = datetime(2024, 4, 30, 8, 5, 0, tzinfo=UTC).timestamp()
            os.utime(closed_path, (old_mtime, old_mtime))

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                runtime = LogMaintenanceRuntime(
                    MaintenanceConfig(
                        root_dir=root_dir,
                        min_age_seconds=60,
                        retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                        max_total_bytes=None,
                        min_free_bytes=None,
                    )
                )
                summary = runtime.run_startup_cleanup()

            self.assertEqual(summary.compressed_files, 1)
            self.assertFalse(closed_path.exists())
            self.assertTrue(compressed_path.exists())
            with gzip.open(compressed_path, "rt", encoding="utf-8") as compressed:
                self.assertEqual(compressed.read(), '{"event":"old"}\n{"event":"new"}\n')

    def test_maintenance_compression_failure_cleans_partial_gzip_and_skips(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            closed_path = root_dir / "error/2024/04/30/api.test.api-test.pid-321.error.20240430.part-001.jsonl"
            closed_path.parent.mkdir(parents=True, exist_ok=True)
            closed_path.write_text('{"event":"error"}\n', encoding="utf-8")
            old_mtime = datetime(2024, 4, 30, 8, 5, 0, tzinfo=UTC).timestamp()
            os.utime(closed_path, (old_mtime, old_mtime))

            def flaky_copyfileobj(source, target, *args, **kwargs):
                target.write(b"partial")
                raise OSError("copy failed")

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                with patch("quantagent.api.observability.maintenance.shutil.copyfileobj", side_effect=flaky_copyfileobj):
                    runtime = LogMaintenanceRuntime(
                        MaintenanceConfig(
                            root_dir=root_dir,
                            min_age_seconds=60,
                            retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                            max_total_bytes=None,
                            min_free_bytes=None,
                        )
                    )
                    summary = runtime.run_startup_cleanup()

            self.assertEqual(summary.compressed_files, 0)
            self.assertGreaterEqual(summary.skipped_files, 1)
            self.assertTrue(closed_path.exists())
            self.assertFalse(closed_path.with_suffix(".jsonl.gz").exists())
            self.assertFalse(closed_path.with_suffix(".jsonl.gz.tmp").exists())

    def test_maintenance_applies_stream_specific_retention(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            access_path = root_dir / "access/2024/05/01/api.test.api-test.pid-321.access.20240501.jsonl"
            error_path = root_dir / "error/2024/05/01/api.test.api-test.pid-321.error.20240501.jsonl"
            for path in (access_path, error_path):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"event":"x"}\n', encoding="utf-8")
                old_mtime = datetime(2024, 5, 1, 6, 5, 0, tzinfo=UTC).timestamp()
                os.utime(path, (old_mtime, old_mtime))

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 10, 12, 0, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                runtime = LogMaintenanceRuntime(
                    MaintenanceConfig(
                        root_dir=root_dir,
                        min_age_seconds=60,
                        retention_days=StreamRetentionDays(access=1, app=14, error=30, security=30, audit=90),
                        max_total_bytes=None,
                        min_free_bytes=None,
                    )
                )
                summary = runtime.run_startup_cleanup()

            self.assertGreaterEqual(summary.deleted_files, 1)
            self.assertFalse(access_path.exists())
            self.assertTrue(error_path.with_suffix(".jsonl.gz").exists())

    def test_maintenance_shutdown_can_process_closed_active_file_without_rewriting(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            active_path = root_dir / "audit/2024/05/01/api.test.api-test.pid-321.audit.20240501.jsonl"
            active_path.parent.mkdir(parents=True, exist_ok=True)
            active_path.write_text('{"event":"audit"}\n', encoding="utf-8")
            mtime = datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC).timestamp()
            os.utime(active_path, (mtime, mtime))

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 1, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                runtime = LogMaintenanceRuntime(
                    MaintenanceConfig(
                        root_dir=root_dir,
                        min_age_seconds=300,
                        retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                        max_total_bytes=None,
                        min_free_bytes=None,
                    )
                )
                summary = runtime.run_shutdown_cleanup(force_closed_paths={active_path})

            self.assertEqual(summary.compressed_files, 1)
            self.assertFalse(active_path.exists())
            self.assertTrue(active_path.with_suffix(".jsonl.gz").exists())

    def test_logging_shutdown_compresses_paths_created_during_queue_drain(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=root_dir,
                    service="api",
                    env="test",
                    instance_id="api-test",
                    pid=321,
                    rotate_max_bytes=1024 * 1024,
                )
            )
            queue_runtime = QueueWriterRuntime(
                writer_set=writer_set,
                max_size=16,
                access_drop_when_full=True,
                shutdown_timeout_seconds=2.0,
            )
            maintenance_runtime = LogMaintenanceRuntime(
                MaintenanceConfig(
                    root_dir=root_dir,
                    min_age_seconds=300,
                    retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                    max_total_bytes=None,
                    min_free_bytes=None,
                )
            )
            runtime = _LoggingRuntime(
                config=SimpleNamespace(),  # type: ignore[arg-type]
                queue_runtime=queue_runtime,
                handler=logging.NullHandler(),
                maintenance_runtime=maintenance_runtime,
            )
            queue_runtime.start()

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 1, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                queue_runtime.enqueue(stream="access", line='{"event":"access"}', created_at=fixed_now.timestamp())
                runtime.shutdown()

            active_path = root_dir / "access/2024/05/01/api.test.api-test.pid-321.access.20240501.jsonl"
            self.assertFalse(active_path.exists())
            self.assertTrue(active_path.with_suffix(".jsonl.gz").exists())

    def test_logging_shutdown_merges_same_day_same_pid_file_after_container_restart(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            active_path = root_dir / "app/2024/05/01/api.local.api-local-dev.pid-1.app.20240501.jsonl"
            compressed_path = active_path.with_suffix(".jsonl.gz")
            active_path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(compressed_path, "wt", encoding="utf-8") as compressed:
                compressed.write('{"event":"previous-run"}\n')
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=root_dir,
                    service="api",
                    env="local",
                    instance_id="api-local-dev",
                    pid=1,
                    rotate_max_bytes=1024 * 1024,
                )
            )
            queue_runtime = QueueWriterRuntime(
                writer_set=writer_set,
                max_size=16,
                access_drop_when_full=True,
                shutdown_timeout_seconds=2.0,
            )
            maintenance_runtime = LogMaintenanceRuntime(
                MaintenanceConfig(
                    root_dir=root_dir,
                    min_age_seconds=300,
                    retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                    max_total_bytes=None,
                    min_free_bytes=None,
                )
            )
            runtime = _LoggingRuntime(
                config=SimpleNamespace(),  # type: ignore[arg-type]
                queue_runtime=queue_runtime,
                handler=logging.NullHandler(),
                maintenance_runtime=maintenance_runtime,
            )
            queue_runtime.start()

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 1, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                self.assertTrue(queue_runtime.enqueue(stream="app", line='{"event":"current-run"}', created_at=fixed_now.timestamp()))
                runtime.shutdown()

            self.assertFalse(active_path.exists())
            self.assertTrue(compressed_path.exists())
            with gzip.open(compressed_path, "rt", encoding="utf-8") as compressed:
                self.assertEqual(compressed.read(), '{"event":"previous-run"}\n{"event":"current-run"}\n')

    def test_logging_shutdown_compresses_same_day_size_rotated_parts(self) -> None:
        from datetime import UTC, datetime

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_dir = Path(tmp_dir)
            writer_set = StreamFileWriterSet(
                FileLayoutConfig(
                    root_dir=root_dir,
                    service="api",
                    env="test",
                    instance_id="api-test",
                    pid=321,
                    rotate_max_bytes=24,
                )
            )
            queue_runtime = QueueWriterRuntime(
                writer_set=writer_set,
                max_size=16,
                access_drop_when_full=True,
                shutdown_timeout_seconds=2.0,
            )
            maintenance_runtime = LogMaintenanceRuntime(
                MaintenanceConfig(
                    root_dir=root_dir,
                    min_age_seconds=300,
                    retention_days=StreamRetentionDays(access=7, app=7, error=7, security=7, audit=7),
                    max_total_bytes=None,
                    min_free_bytes=None,
                )
            )
            runtime = _LoggingRuntime(
                config=SimpleNamespace(),  # type: ignore[arg-type]
                queue_runtime=queue_runtime,
                handler=logging.NullHandler(),
                maintenance_runtime=maintenance_runtime,
            )
            queue_runtime.start()

            with patch("quantagent.api.observability.maintenance.datetime") as datetime_mock:
                fixed_now = datetime(2024, 5, 1, 10, 1, 0, tzinfo=UTC)
                datetime_mock.now.return_value = fixed_now
                datetime_mock.fromtimestamp = datetime.fromtimestamp
                datetime_mock.strptime = datetime.strptime
                for index in range(3):
                    self.assertTrue(
                        queue_runtime.enqueue(
                            stream="access",
                            line=f'{{"event":"access","index":{index}}}',
                            created_at=fixed_now.timestamp(),
                        )
                    )
                runtime.shutdown()

            jsonl_paths = sorted((root_dir / "access/2024/05/01").glob("*.jsonl"))
            gzip_paths = sorted((root_dir / "access/2024/05/01").glob("*.jsonl.gz"))
            self.assertEqual(jsonl_paths, [])
            self.assertEqual(len(gzip_paths), 3)


if __name__ == "__main__":
    unittest.main()
