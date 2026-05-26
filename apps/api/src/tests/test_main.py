from __future__ import annotations

import unittest

from quantagent.api.config.settings import Settings
from quantagent.api.main import _should_enable_reload


class ApiMainTestCase(unittest.TestCase):
    def test_local_dev_entrypoint_enables_reload_only_for_local_envs(self) -> None:
        self.assertTrue(_should_enable_reload(Settings(APP_ENV="development")))
        self.assertTrue(_should_enable_reload(Settings(APP_ENV="local")))
        self.assertFalse(
            _should_enable_reload(
                Settings(
                    APP_ENV="production",
                    AUTH_ADMIN_PASSWORD="prod-password",
                    AUTH_SESSION_SECRET="prod-secret",
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
