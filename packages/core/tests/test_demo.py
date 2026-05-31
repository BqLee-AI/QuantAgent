from __future__ import annotations

import asyncio
import unittest

from quantagent.core.demo import PLACEHOLDER_PLUGIN_ID, run_demo


class QuantagentDemoTestCase(unittest.TestCase):
    def test_run_demo_emits_human_readable_pipeline_output(self) -> None:
        result = asyncio.run(run_demo())

        self.assertEqual(result.exit_code, 0)
        self.assertIn("🔍 Scanning plugins...", result.output)
        self.assertIn(PLACEHOLDER_PLUGIN_ID, result.output)
        self.assertIn("🚀 Triggering plugin: source.fetch", result.output)
        self.assertIn("📤 Event published to: source.event.captured", result.output)
        self.assertIn("📩 Consumer received event!", result.output)
        self.assertIn("✨ Demo complete! The full pipeline works.", result.output)
