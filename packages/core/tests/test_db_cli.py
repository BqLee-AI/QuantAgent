from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from quantagent.core.config.settings import settings
from quantagent.core.db import cli


class DatabaseCliTestCase(unittest.TestCase):
    def test_alembic_config_uses_core_migration_directory(self) -> None:
        config = cli.create_alembic_config()
        script_location = config.get_main_option("script_location")

        self.assertIsNotNone(script_location)
        self.assertTrue(Path(script_location).is_absolute())
        self.assertEqual(Path(script_location).name, "alembic")
        self.assertTrue(Path(script_location).exists())

    def test_migration_root_can_be_configured_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "alembic.ini").write_text("[alembic]\nscript_location = alembic\n", encoding="utf-8")
            (root / "alembic").mkdir()

            with patch.dict("os.environ", {cli.MIGRATION_ROOT_ENV: str(root)}):
                config = cli.create_alembic_config()

        self.assertEqual(Path(config.config_file_name).parent, root)
        self.assertEqual(Path(config.get_main_option("script_location")), root / "alembic")

    def test_invalid_migration_root_fails_before_running_alembic(self) -> None:
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(settings, "DATABASE_URL", "sqlite:///:memory:"):
                with patch.dict("os.environ", {cli.MIGRATION_ROOT_ENV: temp_dir}):
                    with patch("quantagent.core.db.cli.command.current") as current:
                        with redirect_stderr(stderr):
                            exit_code = cli.main(["current"])

        self.assertEqual(exit_code, 2)
        self.assertIn(cli.MIGRATION_ROOT_ENV, stderr.getvalue())
        current.assert_not_called()

    def test_migration_root_can_be_discovered_from_repo_root_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            migration_root = repo_root / "packages" / "core"
            migration_root.mkdir(parents=True)
            (migration_root / "alembic.ini").write_text(
                "[alembic]\nscript_location = alembic\n",
                encoding="utf-8",
            )
            (migration_root / "alembic").mkdir()

            with patch("quantagent.core.db.cli.Path.cwd", return_value=repo_root / "apps" / "api"):
                config = cli.create_alembic_config()

        self.assertEqual(Path(config.config_file_name).parent, migration_root)
        self.assertEqual(Path(config.get_main_option("script_location")), migration_root / "alembic")

    def test_migration_root_discovers_repo_layout_from_module_file_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            migration_root = repo_root / "packages" / "core"
            migration_root.mkdir(parents=True)
            (migration_root / "alembic.ini").write_text(
                "[alembic]\nscript_location = alembic\n",
                encoding="utf-8",
            )
            (migration_root / "alembic").mkdir()
            module_file = repo_root / "venv" / "lib" / "python3.13" / "site-packages" / "quantagent" / "core" / "db" / "cli.py"
            module_file.parent.mkdir(parents=True)
            module_file.write_text("# test stub\n", encoding="utf-8")

            with patch.dict("os.environ", {}, clear=True):
                with patch("quantagent.core.db.cli.Path.cwd", return_value=Path("/nonexistent")):
                    with patch("quantagent.core.db.cli.__file__", str(module_file)):
                        config = cli.create_alembic_config()

        self.assertEqual(Path(config.config_file_name).parent, migration_root)
        self.assertEqual(Path(config.get_main_option("script_location")), migration_root / "alembic")

    def test_upgrade_defaults_to_head(self) -> None:
        with patch.object(settings, "DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.core.db.cli.command.upgrade") as upgrade:
                exit_code = cli.main(["upgrade"])

        self.assertEqual(exit_code, 0)
        upgrade.assert_called_once()
        self.assertEqual(upgrade.call_args.args[1], "head")

    def test_current_invokes_alembic_current(self) -> None:
        with patch.object(settings, "DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.core.db.cli.command.current") as current:
                exit_code = cli.main(["current"])

        self.assertEqual(exit_code, 0)
        current.assert_called_once()

    def test_check_invokes_alembic_check(self) -> None:
        with patch.object(settings, "DATABASE_URL", "sqlite:///:memory:"):
            with patch("quantagent.core.db.cli.command.check") as check:
                exit_code = cli.main(["check"])

        self.assertEqual(exit_code, 0)
        check.assert_called_once()

    def test_database_url_is_required_without_leaking_values(self) -> None:
        stderr = io.StringIO()

        with patch.object(settings, "DATABASE_URL", None):
            with patch("quantagent.core.db.cli.command.current") as current:
                with redirect_stderr(stderr):
                    exit_code = cli.main(["current"])

        self.assertEqual(exit_code, 2)
        self.assertIn("DATABASE_URL must be configured", stderr.getvalue())
        current.assert_not_called()

    def test_database_url_override_is_scoped_to_single_command(self) -> None:
        with patch.object(settings, "DATABASE_URL", "postgresql://original"):
            with patch.dict("os.environ", {}, clear=True):
                with cli._database_url_override("postgresql://override"):
                    self.assertEqual(settings.DATABASE_URL, "postgresql://override")
                    self.assertEqual(cli.os.environ["DATABASE_URL"], "postgresql://override")

                self.assertEqual(settings.DATABASE_URL, "postgresql://original")
                self.assertNotIn("DATABASE_URL", cli.os.environ)

    def test_database_url_override_restores_previous_env_value(self) -> None:
        with patch.object(settings, "DATABASE_URL", "postgresql://original"):
            with patch.dict("os.environ", {"DATABASE_URL": "postgresql://env-original"}, clear=True):
                with cli._database_url_override("postgresql://override"):
                    self.assertEqual(settings.DATABASE_URL, "postgresql://override")
                    self.assertEqual(cli.os.environ["DATABASE_URL"], "postgresql://override")

                self.assertEqual(settings.DATABASE_URL, "postgresql://original")
                self.assertEqual(cli.os.environ["DATABASE_URL"], "postgresql://env-original")


if __name__ == "__main__":
    unittest.main()
