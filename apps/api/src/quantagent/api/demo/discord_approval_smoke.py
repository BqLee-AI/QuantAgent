from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import dotenv_values
from fastapi import Request
from fastapi.responses import JSONResponse

from quantagent.api.config.settings import Settings
from quantagent.api.main import create_app
from quantagent.core.approval import (
    ActionRequest,
    ApprovalEventPublisher,
    ApprovalInput,
    ApprovalNotificationHandoffAdapter,
    ApprovalOrchestrationService,
    FakeActionExecutor,
    FakePolicyGate,
    InMemoryApprovalRepository,
)
from quantagent.core.events import EventEnvelope, InMemoryEventBus
from quantagent.core.notifications import NotificationDispatchService, NotificationEventPublisher, NotificationRequestedHandler
from quantagent.core.registry import PluginManifest, PluginRecord, PluginSource, PluginStatus, PluginType
from quantagent.core.runtime import PluginRuntimeService
from quantagent.plugin_sdk.io import to_json_value

PLUGIN_ID = "quantagent.official.notification.discord"
DEFAULT_APPROVAL_ID = "approval-fullflow"
DEFAULT_ACTION_ID = "action-fullflow"


class _DiscordNotificationRegistry:
    def __init__(self, *, plugin_path: Path) -> None:
        self._plugin_path = plugin_path

    def get_plugin(self, plugin_id: str) -> PluginRecord | None:
        if plugin_id != PLUGIN_ID:
            return None
        return PluginRecord(
            id=PLUGIN_ID,
            source=PluginSource.OFFICIAL,
            path=self._plugin_path,
            status=PluginStatus.VALID,
            manifest=PluginManifest(
                id=PLUGIN_ID,
                name="Discord Notification",
                type=PluginType.NOTIFICATION,
                version="0.1.0",
                entrypoint="src.discord_plugin:plugin",
                capabilities=("notification.send", "notification.receive"),
                config_schema="config.schema.json",
            ),
        )


class _RecordingHandler:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        self.events.append(envelope)


class DiscordApprovalSmokeHarness:
    """本地 smoke harness：只在显式命令运行时暴露 debug 路由。"""

    def __init__(self, *, repo_root: Path, approval_id: str, action_id: str) -> None:
        self.repo_root = repo_root
        self.approval_id = approval_id
        self.action_id = action_id
        self.bus = InMemoryEventBus()
        self.repository = InMemoryApprovalRepository()
        self.executor = FakeActionExecutor()
        self.gate = FakePolicyGate(allowed=True)
        self.notification_completed = _RecordingHandler()
        self.approval_completed = _RecordingHandler()
        self.service = ApprovalOrchestrationService(
            repository=self.repository,
            event_publisher=ApprovalEventPublisher(self.bus),
            policy_gate=self.gate,
            executor=self.executor,
            id_factory=lambda prefix: approval_id if prefix == "approval" else f"{prefix}-fullflow",
        )

    async def seed_and_send(self) -> None:
        await self.bus.subscribe(topics=("notification.completed",), group_id="debug", handler=self.notification_completed)
        await self.bus.subscribe(topics=("approval.completed",), group_id="debug", handler=self.approval_completed)
        dispatch = NotificationDispatchService(
            registry=_DiscordNotificationRegistry(plugin_path=self.repo_root / "plugins" / "notifications" / "discord"),
            runtime=PluginRuntimeService(),
            config={
                "webhook_secret_ref": "env:DISCORD_WEBHOOK_URL",
                "__secrets__": {"env:DISCORD_WEBHOOK_URL": self._discord_webhook_url()},
            },
        )
        await self.bus.subscribe(
            topics=("notification.requested",),
            group_id="notification-dispatch",
            handler=NotificationRequestedHandler(
                dispatch_service=dispatch,
                event_publisher=NotificationEventPublisher(self.bus),
                plugin_id=PLUGIN_ID,
            ),
        )
        await self.service.submit_action(
            ActionRequest(
                id=self.action_id,
                action_type="adjust_strategy",
                action_side="increase_risk",
                target_type="strategy",
                target_id="strategy-fullflow",
                correlation_id="corr-fullflow",
                proposed_payload={"smoke": True, "path": "discord-fullflow"},
            )
        )

    async def strong_confirm(self) -> dict[str, Any]:
        result = await self.service.submit_input(
            ApprovalInput(
                id="input-strong-fullflow",
                approval_id=self.approval_id,
                channel="web",
                actor_ref="debug:strong-confirm",
                structured_payload={"intent": "approve"},
            )
        )
        return {
            "approval": to_json_value(result.approval.to_mapping()) if result.approval else None,
            "evaluation": to_json_value(result.evaluation.to_mapping()) if result.evaluation else None,
            "decision": to_json_value(result.decision.to_mapping()) if result.decision else None,
            "executor_calls": len(self.executor.calls),
            "gate_calls": len(self.gate.calls),
        }

    def status(self) -> dict[str, Any]:
        approval = self.repository.get_approval_request(self.approval_id)
        inputs = self.repository.list_inputs(self.approval_id)
        evaluations = self.repository.list_evaluations(self.approval_id)
        decisions = self.repository.list_decisions(self.approval_id)
        return {
            "approval_id": self.approval_id,
            "action_id": self.action_id,
            "approval_status": approval.status.value if approval else None,
            "input_count": len(inputs),
            "latest_input": to_json_value(inputs[-1].to_mapping()) if inputs else None,
            "latest_evaluation": to_json_value(evaluations[-1].to_mapping()) if evaluations else None,
            "latest_decision": to_json_value(decisions[-1].to_mapping()) if decisions else None,
            "decision_count": len(decisions),
            "executor_calls": len(self.executor.calls),
            "gate_calls": len(self.gate.calls),
            "notification_completed_count": len(self.notification_completed.events),
            "notification_completed_payloads": [_notification_summary(event) for event in self.notification_completed.events],
            "approval_completed_count": len(self.approval_completed.events),
        }

    def _discord_webhook_url(self) -> str:
        value = os.environ.get("DISCORD_WEBHOOK_URL")
        if value:
            return value.strip()
        dotenv_value = dotenv_values(self.repo_root / ".env").get("DISCORD_WEBHOOK_URL")
        return str(dotenv_value or "").strip()


def build_app(*, settings: Settings, harness: DiscordApprovalSmokeHarness):
    app = create_app(settings)
    app.state.notification_approval_handoff = ApprovalNotificationHandoffAdapter(service=harness.service)

    @app.middleware("http")
    async def smoke_access_log(request: Request, call_next):
        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
        summary = _interaction_summary(request.url.path, body)
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/debug/fullflow") or request.url.path == "/api/v1/integrations/notifications/ingress":
            logging.info(
                "request method=%s path=%s status=%s summary=%s",
                request.method,
                request.url.path,
                response.status_code,
                summary,
            )
        return response

    @app.get("/api/v1/debug/fullflow")
    async def fullflow_status():
        return JSONResponse(harness.status())

    @app.post("/api/v1/debug/fullflow/strong-confirm")
    async def fullflow_strong_confirm():
        return JSONResponse(await harness.strong_confirm())

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Discord approval fullflow smoke harness.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--approval-id", default=DEFAULT_APPROVAL_ID)
    parser.add_argument("--action-id", default=DEFAULT_ACTION_ID)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="FULLFLOW %(asctime)s %(message)s")
    repo_root = _repo_root()
    harness = DiscordApprovalSmokeHarness(repo_root=repo_root, approval_id=args.approval_id, action_id=args.action_id)
    asyncio.run(harness.seed_and_send())
    status = harness.status()
    send_payloads = status["notification_completed_payloads"]
    logging.info(
        "seed action=%s approval=%s status=%s notification_completed=%s",
        args.action_id,
        args.approval_id,
        status["approval_status"],
        status["notification_completed_count"],
    )
    if send_payloads:
        logging.info(
            "notification.completed accepted=%s code=%s message=%s",
            send_payloads[-1].get("accepted"),
            send_payloads[-1].get("code"),
            send_payloads[-1].get("message"),
        )
    uvicorn.run(build_app(settings=Settings(), harness=harness), host=args.host, port=args.port, access_log=True)
    return 0


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "apps").is_dir() and (parent / "plugins").is_dir():
            return parent
    raise RuntimeError("Repository root could not be resolved.")


def _notification_summary(event: EventEnvelope) -> dict[str, Any]:
    payload = to_json_value(event.payload)
    if not isinstance(payload, Mapping):
        return {"topic": event.topic}
    return {
        "topic": event.topic,
        "accepted": payload.get("accepted"),
        "code": payload.get("code"),
        "message": payload.get("message"),
        "approval_id": payload.get("approval_id"),
        "action_request_id": payload.get("action_request_id"),
    }


def _interaction_summary(path: str, body: bytes) -> dict[str, Any]:
    if path != "/api/v1/integrations/notifications/ingress" or not body:
        return {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return {"payload": "invalid-json"}
    if not isinstance(payload, Mapping):
        return {"payload": "not-object"}
    data = payload.get("data") if isinstance(payload.get("data"), Mapping) else {}
    options = data.get("options") if isinstance(data.get("options"), list) else []
    member = payload.get("member") if isinstance(payload.get("member"), Mapping) else {}
    user = payload.get("user") if isinstance(payload.get("user"), Mapping) else member.get("user") if isinstance(member.get("user"), Mapping) else {}
    return {
        "type": payload.get("type"),
        "application_id": payload.get("application_id"),
        "command": data.get("name"),
        "option_names": [option.get("name") for option in options if isinstance(option, Mapping)],
        "has_guild_id": bool(payload.get("guild_id")),
        "has_channel_id": bool(payload.get("channel_id")),
        "has_author_id": bool(user.get("id")),
    }


if __name__ == "__main__":
    raise SystemExit(main())
