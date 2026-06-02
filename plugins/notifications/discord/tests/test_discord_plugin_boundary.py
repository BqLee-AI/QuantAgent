from __future__ import annotations

import ast
import unittest
from pathlib import Path


class DiscordPluginBoundaryTestCase(unittest.TestCase):
    def test_plugin_does_not_import_platform_approval_or_api_boundaries(self) -> None:
        source_path = Path(__file__).resolve().parents[1] / "src" / "discord_plugin.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        forbidden_prefixes = (
            "quantagent.core.approval",
            "quantagent.core.events",
            "quantagent.api",
            "apps.api",
        )
        for imported in imports:
            self.assertFalse(
                imported.startswith(forbidden_prefixes),
                f"Discord notification plugin must remain protocol-only, found import {imported!r}",
            )


if __name__ == "__main__":
    unittest.main()
