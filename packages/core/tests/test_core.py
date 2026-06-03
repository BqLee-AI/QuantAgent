from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.engine import Engine

from quantagent.core.config.settings import Settings, _SOURCE_REPO_ROOT
from quantagent.core.db.base import Base
from quantagent.core.db import wallet_models
from quantagent.core.db.session import create_session_factory, create_sync_engine, require_database_url, settings as db_settings
from quantagent.core.model_config import orm as model_config_orm


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

    def test_database_url_has_no_hardcoded_default(self) -> None:
        settings = Settings(_env_file=None)

        self.assertIsNone(settings.DATABASE_URL)

    def test_runtime_dir_defaults_to_repo_root_runtime_when_unset(self) -> None:
        settings = Settings(_env_file=None)

        expected = (_SOURCE_REPO_ROOT / "runtime") if _SOURCE_REPO_ROOT is not None else Path("runtime")
        self.assertEqual(settings.RUNTIME_DIR, expected)

    def test_runtime_dir_blank_value_uses_repo_root_runtime_default(self) -> None:
        settings = Settings(_env_file=None, RUNTIME_DIR="")

        expected = (_SOURCE_REPO_ROOT / "runtime") if _SOURCE_REPO_ROOT is not None else Path("runtime")
        self.assertEqual(settings.RUNTIME_DIR, expected)

    def test_runtime_dir_preserves_explicit_absolute_path(self) -> None:
        settings = Settings(_env_file=None, RUNTIME_DIR="/tmp/quantagent-runtime")

        self.assertEqual(settings.RUNTIME_DIR, Path("/tmp/quantagent-runtime"))

    def test_runtime_dir_preserves_explicit_relative_path(self) -> None:
        settings = Settings(_env_file=None, RUNTIME_DIR="./runtime-dev")

        self.assertEqual(settings.RUNTIME_DIR, Path("./runtime-dev"))

    def test_base_metadata_is_importable(self) -> None:
        self.assertIsNotNone(Base.metadata)
        self.assertIn("trading_accounts", Base.metadata.tables)
        self.assertIn("wallet_ledger_entries", Base.metadata.tables)
        self.assertIn("model_providers", Base.metadata.tables)
        self.assertIn("model_invocations", Base.metadata.tables)
        self.assertIn("raw_events", Base.metadata.tables)
        self.assertIn("event_intake_routed_events", Base.metadata.tables)
        self.assertIn("ix_model_invocations_created_at", {index.name for index in Base.metadata.tables["model_invocations"].indexes})

    def test_database_url_is_required_for_default_engine(self) -> None:
        with patch.object(db_settings, "DATABASE_URL", None):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL must be configured"):
                require_database_url()

    def test_sync_engine_and_session_factory_are_importable(self) -> None:
        engine = create_sync_engine("sqlite:///:memory:")
        session_factory = create_session_factory(engine)

        self.assertIsInstance(engine, Engine)
        self.assertFalse(session_factory.kw["autoflush"])
        self.assertFalse(session_factory.kw["expire_on_commit"])


if __name__ == "__main__":
    unittest.main()
