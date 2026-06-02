from __future__ import annotations

import unittest
from unittest.mock import patch

from quantagent.core.events import InMemoryEventBus
from quantagent.worker.main import create_worker_app, create_worker_runtime, run, run_once


class WorkerMainTestCase(unittest.IsolatedAsyncioTestCase):
    def test_worker_runtime_uses_memory_backend_by_default(self) -> None:
        with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
            runtime = create_worker_runtime()
        self.assertEqual(runtime.backend, "memory")
        self.assertIsInstance(runtime.publisher, InMemoryEventBus)

    def test_create_worker_app_requires_database_url(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", None):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL must be configured"):
                create_worker_app()

    def test_create_worker_app_builds_handler_when_database_url_exists(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
                app = create_worker_app()
        self.assertEqual(app.runtime.backend, "memory")
        self.assertIsNotNone(app.handler)
        app.session.close()

    def test_create_worker_app_uses_topic_publishing_gateway(self) -> None:
        with patch("quantagent.worker.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
                app = create_worker_app()
        gateway = app.handler.routing_service._industry_gateway
        self.assertEqual(gateway.__class__.__name__, "TopicPublishingIndustryGateway")
        app.session.close()

    async def test_run_once_consumes_once_and_closes_app(self) -> None:
        app = _FakeWorkerApp()
        with patch("quantagent.worker.main.create_worker_app", return_value=app):
            await run_once()

        self.assertEqual(app.consumed_once, 1)
        self.assertEqual(app.closed, 1)

    def test_run_executes_run_once(self) -> None:
        calls = []

        async def fake_run_once() -> None:
            calls.append("run_once")

        with patch("quantagent.worker.main.run_once", fake_run_once):
            run()

        self.assertEqual(calls, ["run_once"])


class _FakeWorkerApp:
    consumed_once = 0
    closed = 0

    async def consume_once(self) -> None:
        self.consumed_once += 1

    async def close(self) -> None:
        self.closed += 1


if __name__ == "__main__":
    unittest.main()
