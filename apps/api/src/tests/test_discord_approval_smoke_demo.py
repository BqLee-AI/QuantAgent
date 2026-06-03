from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from quantagent.api.config.settings import Settings
from quantagent.api.demo import discord_approval_smoke
from quantagent.api.main import create_app
from quantagent.core.notifications.models import NotificationDispatchResult


class _FakeDispatchService:
    def __init__(self, **_kwargs) -> None:
        pass

    async def dispatch(self, request):
        return NotificationDispatchResult(
            request_id=request.request_id,
            plugin_id=request.plugin_id,
            accepted=True,
            retryable=False,
            code="SENT",
            message="fake Discord webhook notification sent.",
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            approval_id=request.approval_id,
            action_request_id=request.action_request_id,
            channel=request.channel,
        )


class DiscordApprovalSmokeDemoTestCase(unittest.TestCase):
    def _settings(self) -> Settings:
        return Settings(
            _env_file=None,
            APP_ENV="development",
            DATABASE_URL=None,
            AUTH_ENABLED=False,
            NOTIFICATION_INGRESS_ENABLED=False,
            NOTIFICATION_INGRESS_PLUGIN_ID="",
            NOTIFICATION_INGRESS_PLUGIN_CONFIG={},
        )

    def test_regular_api_does_not_expose_fullflow_debug_route(self) -> None:
        with TestClient(create_app(self._settings())) as client:
            response = client.get("/api/v1/debug/fullflow")

        self.assertEqual(response.status_code, 404)

    def test_smoke_app_exposes_debug_route_only_for_harness(self) -> None:
        harness = discord_approval_smoke.DiscordApprovalSmokeHarness(
            repo_root=Path.cwd(),
            approval_id="approval-fullflow",
            action_id="action-fullflow",
        )
        with patch.object(discord_approval_smoke, "NotificationDispatchService", _FakeDispatchService):
            asyncio.run(harness.seed_and_send())

        app = discord_approval_smoke.build_app(settings=self._settings(), harness=harness)
        with TestClient(app) as client:
            response = client.get("/api/v1/debug/fullflow")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["approval_id"], "approval-fullflow")
        self.assertEqual(payload["approval_status"], "pending")
        self.assertEqual(payload["notification_completed_count"], 1)
        self.assertEqual(payload["notification_completed_payloads"][0]["code"], "SENT")


if __name__ == "__main__":
    unittest.main()
