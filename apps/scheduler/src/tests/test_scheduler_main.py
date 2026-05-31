from __future__ import annotations

import unittest
from unittest.mock import patch

from quantagent.core.events import InMemoryEventBus
from quantagent.scheduler.main import create_scheduler_runtime


class SchedulerMainTestCase(unittest.TestCase):
    def test_scheduler_runtime_uses_memory_backend_by_default(self) -> None:
        with patch("quantagent.scheduler.main.settings.EVENT_BUS_BACKEND", "memory"):
            runtime = create_scheduler_runtime()
        self.assertEqual(runtime.backend, "memory")
        self.assertIsInstance(runtime.publisher, InMemoryEventBus)


if __name__ == "__main__":
    unittest.main()
