from __future__ import annotations

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from quantagent.api.config.settings import Settings
from quantagent.api.main import (
    _DEV_WORKER_PID_TRACKING_ENV,
    _PID_ROLE_RELOADER,
    _PID_ROLE_WORKER,
    _cleanup_stale_dev_server_pid_files,
    _collect_dev_server_pids,
    _dev_server_pid_path,
    create_app,
    _should_enable_reload,
    _stop_dev_server,
    _write_dev_server_pid,
)


class ApiMainTestCase(unittest.TestCase):
    def test_local_dev_entrypoint_enables_reload_only_for_local_envs(self) -> None:
        self.assertTrue(_should_enable_reload(Settings(APP_ENV="development")))
        self.assertTrue(_should_enable_reload(Settings(APP_ENV="local")))
        self.assertFalse(
            _should_enable_reload(
                Settings(
                    APP_ENV="production",
                    AUTH_ADMIN_PASSWORD="prod-password-for-entrypoint-test",
                    AUTH_SESSION_SECRET="prod-session-secret-for-entrypoint-test",
                    AUTH_COOKIE_SECURE=True,
                )
            )
        )

    def test_dev_server_pid_files_live_under_runtime_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                _env_file=None,
                APP_ENV="development",
                DATABASE_URL=None,
                RUNTIME_DIR=tmp_dir,
                AUTH_ENABLED=False,
            )

            reloader_path = _dev_server_pid_path(settings, _PID_ROLE_RELOADER)
            worker_path = _dev_server_pid_path(settings, _PID_ROLE_WORKER)

            self.assertEqual(reloader_path, Path(tmp_dir) / "data/api/dev-server/reloader.pid")
            self.assertEqual(worker_path, Path(tmp_dir) / "data/api/dev-server/worker.pid")

    def test_development_lifespan_does_not_write_dev_worker_pid_without_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                _env_file=None,
                APP_ENV="development",
                DATABASE_URL=None,
                RUNTIME_DIR=tmp_dir,
                AUTH_ENABLED=False,
            )
            worker_path = _dev_server_pid_path(settings, _PID_ROLE_WORKER)

            with patch.dict(os.environ, {_DEV_WORKER_PID_TRACKING_ENV: ""}, clear=False):
                with TestClient(create_app(settings)) as client:
                    response = client.get("/api/v1/health")

            self.assertEqual(response.status_code, 200)
            self.assertFalse(worker_path.exists())

    def test_development_lifespan_writes_dev_worker_pid_when_opted_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                _env_file=None,
                APP_ENV="development",
                DATABASE_URL=None,
                RUNTIME_DIR=tmp_dir,
                AUTH_ENABLED=False,
            )
            worker_path = _dev_server_pid_path(settings, _PID_ROLE_WORKER)
            observed_during_lifespan = False

            with patch.dict(os.environ, {_DEV_WORKER_PID_TRACKING_ENV: "1"}, clear=False):
                with TestClient(create_app(settings)) as client:
                    response = client.get("/api/v1/health")
                    observed_during_lifespan = worker_path.exists()

            self.assertEqual(response.status_code, 200)
            self.assertTrue(observed_during_lifespan)
            self.assertFalse(worker_path.exists())

    def test_production_lifespan_does_not_write_dev_worker_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                _env_file=None,
                APP_ENV="production",
                DATABASE_URL=None,
                RUNTIME_DIR=tmp_dir,
                AUTH_ADMIN_PASSWORD="prod-password-for-entrypoint-test",
                AUTH_SESSION_SECRET="prod-session-secret-for-entrypoint-test",
                AUTH_COOKIE_SECURE=True,
            )
            worker_path = _dev_server_pid_path(settings, _PID_ROLE_WORKER)

            with TestClient(create_app(settings)) as client:
                response = client.get("/api/v1/health")

            self.assertEqual(response.status_code, 200)
            self.assertFalse(worker_path.exists())

    def test_stop_dev_server_terminates_registered_pids_and_cleans_pid_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                _env_file=None,
                APP_ENV="development",
                DATABASE_URL=None,
                RUNTIME_DIR=tmp_dir,
                AUTH_ENABLED=False,
            )
            _write_dev_server_pid(settings, _PID_ROLE_RELOADER, 101)
            _write_dev_server_pid(settings, _PID_ROLE_WORKER, 202)

            with patch("quantagent.api.main._find_listener_pids", return_value=set()):
                with patch("quantagent.api.main._terminate_processes", return_value=((101, 202), ())):
                    with patch("quantagent.api.main._pid_exists", return_value=False):
                        summary = _stop_dev_server(settings)

            self.assertEqual(summary.terminated_pids, (101, 202))
            self.assertEqual(summary.stubborn_pids, ())
            self.assertIn(_PID_ROLE_RELOADER, summary.stale_pid_files)
            self.assertIn(_PID_ROLE_WORKER, summary.stale_pid_files)
            self.assertFalse(_dev_server_pid_path(settings, _PID_ROLE_RELOADER).exists())
            self.assertFalse(_dev_server_pid_path(settings, _PID_ROLE_WORKER).exists())

    def test_collect_dev_server_pids_falls_back_to_listener_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                _env_file=None,
                APP_ENV="development",
                DATABASE_URL=None,
                RUNTIME_DIR=tmp_dir,
                AUTH_ENABLED=False,
            )

            with patch("quantagent.api.main._find_listener_pids", return_value={303}):
                registered, fallback = _collect_dev_server_pids(settings)

            self.assertEqual(registered, {})
            self.assertEqual(fallback, {303})

    def test_cleanup_stale_dev_server_pid_files_keeps_live_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                _env_file=None,
                APP_ENV="development",
                DATABASE_URL=None,
                RUNTIME_DIR=tmp_dir,
                AUTH_ENABLED=False,
            )
            _write_dev_server_pid(settings, _PID_ROLE_RELOADER, 101)
            _write_dev_server_pid(settings, _PID_ROLE_WORKER, 202)

            with patch("quantagent.api.main._pid_exists", side_effect=lambda pid: pid == 101):
                stale_roles = _cleanup_stale_dev_server_pid_files(settings)

            self.assertEqual(stale_roles, (_PID_ROLE_WORKER,))
            self.assertTrue(_dev_server_pid_path(settings, _PID_ROLE_RELOADER).exists())
            self.assertFalse(_dev_server_pid_path(settings, _PID_ROLE_WORKER).exists())


if __name__ == "__main__":
    unittest.main()
