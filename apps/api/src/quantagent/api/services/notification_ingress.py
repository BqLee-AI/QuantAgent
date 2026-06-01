from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from fastapi import Request
from quantagent.api.http.middleware import get_request_id

from quantagent.api.config.settings import Settings
from quantagent.api.http.errors import BadRequestError, NotFoundError, ServiceUnavailableError
from quantagent.api.services import plugin_registry as plugin_registry_service
from quantagent.core.notifications.ingress import NotificationIngressService, NotificationIngressServiceUnavailableError
from quantagent.core.registry import PluginRegistry
from quantagent.core.runtime import PluginRuntimeService
from quantagent.plugin_sdk import NotificationReceiveInput
from quantagent.plugin_sdk.io import to_json_value


@dataclass(frozen=True)
class NotificationIngressHostHttpResult:
    status_code: int
    content: Mapping[str, object]


class NotificationIngressHostService:
    """通用 notification ingress HTTP host。"""

    def __init__(self, *, settings: Settings, registry: PluginRegistry, runtime: PluginRuntimeService | None = None) -> None:
        self._settings = settings
        self._ingress = NotificationIngressService(registry=registry, runtime=runtime or PluginRuntimeService())

    async def receive_request(
        self,
        *,
        request_id: str,
        headers: Mapping[str, str],
        body: bytes,
        query_params: Mapping[str, str],
        path_params: Mapping[str, str],
    ) -> NotificationIngressHostHttpResult:
        if not self._settings.NOTIFICATION_INGRESS_ENABLED:
            raise NotFoundError("Notification ingress endpoint is not enabled")

        try:
            invocation = await self._ingress.receive(
                plugin_id=self._settings.NOTIFICATION_INGRESS_PLUGIN_ID,
                request_id=request_id,
                config=dict(self._settings.NOTIFICATION_INGRESS_PLUGIN_CONFIG),
                receive_input=NotificationReceiveInput(
                    transport="http.webhook",
                    headers=dict(headers),
                    body_text=body.decode("utf-8", errors="strict"),
                    query_params=dict(query_params),
                    path_params=dict(path_params),
                    request_metadata={
                        "route": "/api/v1/integrations/notifications/ingress",
                        "request_id": request_id,
                    },
                ),
            )
            receive_result = invocation.receive_result
            response = receive_result.response
            if response is None:
                raise ServiceUnavailableError("Configured notification plugin returned an invalid result payload")
            status_code = receive_result.response_status_code
            if status_code is None:
                status_code = 200 if receive_result.accepted else 400
            return NotificationIngressHostHttpResult(status_code=status_code, content=to_json_value(response))
        except UnicodeDecodeError as exc:
            raise BadRequestError("Notification ingress body must be valid utf-8 text") from exc
        except NotificationIngressServiceUnavailableError as exc:
            raise ServiceUnavailableError(str(exc)) from exc


def get_notification_ingress_service(request: Request) -> NotificationIngressHostService:
    service = getattr(request.app.state, "notification_ingress_service", None)
    if service is None:
        service = NotificationIngressHostService(
            settings=request.app.state.settings,
            registry=plugin_registry_service.get_plugin_registry(request),
            runtime=PluginRuntimeService(),
        )
        request.app.state.notification_ingress_service = service
    return service


def get_notification_ingress_request_id(request: Request) -> str:
    return get_request_id(request)
