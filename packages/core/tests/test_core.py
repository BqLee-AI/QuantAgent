from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy.engine import Engine

from quantagent.core.config.settings import Settings
from quantagent.core.db.base import Base
from quantagent.core.db.session import create_session_factory, create_sync_engine


class CorePackageTestCase(unittest.TestCase):
    def test_settings_accept_shared_runtime_values(self) -> None:
        settings = Settings(
            APP_ENV="production",
            DATABASE_URL="sqlite:///:memory:",
            RUNTIME_DIR=Path("/tmp/quantagent-runtime"),
            LOG_LEVEL="DEBUG",
        )

        self.assertTrue(settings.is_production)
        self.assertEqual(settings.DATABASE_URL, "sqlite:///:memory:")
        self.assertEqual(settings.RUNTIME_DIR, Path("/tmp/quantagent-runtime"))
        self.assertEqual(settings.LOG_LEVEL, "DEBUG")

    def test_base_metadata_is_importable(self) -> None:
        self.assertIsNotNone(Base.metadata)
        self.assertEqual(Base.metadata.tables, {})

    def test_sync_engine_and_session_factory_are_importable(self) -> None:
        engine = create_sync_engine("sqlite:///:memory:")
        session_factory = create_session_factory(engine)

        self.assertIsInstance(engine, Engine)
        self.assertFalse(session_factory.kw["autoflush"])
        self.assertFalse(session_factory.kw["expire_on_commit"])


if __name__ == "__main__":
    unittest.main()
