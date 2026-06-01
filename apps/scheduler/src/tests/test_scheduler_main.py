from __future__ import annotations
import unittest
from unittest.mock import patch

from quantagent.core.events import InMemoryEventBus
from quantagent.scheduler.main import create_scheduler_app, create_scheduler_runtime


class SchedulerMainTestCase(unittest.TestCase):
    def test_scheduler_runtime_uses_memory_backend_by_default(self) -> None:
        with patch("quantagent.scheduler.main.settings.EVENT_BUS_BACKEND", "memory"):
            runtime = create_scheduler_runtime()
        self.assertEqual(runtime.backend, "memory")
        self.assertIsInstance(runtime.publisher, InMemoryEventBus)

    def test_create_scheduler_app_requires_database_url(self) -> None:
        with patch("quantagent.scheduler.main.settings.DATABASE_URL", None):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL must be configured"):
                create_scheduler_app()

    def test_create_scheduler_app_builds_loop_service_when_database_url_exists(self) -> None:
        with patch("quantagent.scheduler.main.settings.DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.scheduler.main.settings.EVENT_BUS_BACKEND", "memory"):
                app = create_scheduler_app()
        self.assertIsNotNone(app.loop_service)
        self.assertEqual(app.runtime.backend, "memory")


if __name__ == "__main__":
    unittest.main()
