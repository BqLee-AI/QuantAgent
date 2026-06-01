from __future__ import annotations

import unittest
from unittest.mock import patch

from quantagent.core.events import InMemoryEventBus
from quantagent.worker.main import create_worker_app, create_worker_runtime


class WorkerMainTestCase(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
