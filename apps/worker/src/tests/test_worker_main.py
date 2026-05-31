from __future__ import annotations

import unittest
from unittest.mock import patch

from quantagent.core.events import InMemoryEventBus
from quantagent.worker.main import create_worker_runtime


class WorkerMainTestCase(unittest.TestCase):
    def test_worker_runtime_uses_memory_backend_by_default(self) -> None:
        with patch("quantagent.worker.main.settings.EVENT_BUS_BACKEND", "memory"):
            runtime = create_worker_runtime()
        self.assertEqual(runtime.backend, "memory")
        self.assertIsInstance(runtime.publisher, InMemoryEventBus)


if __name__ == "__main__":
    unittest.main()
