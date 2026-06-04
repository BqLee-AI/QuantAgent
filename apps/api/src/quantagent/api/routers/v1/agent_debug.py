from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from quantagent.api.http.responses import ApiResponse
from quantagent.api.schemas.agent_debug import AgentDebugFixtureSummary, AgentDebugRunRequest
from quantagent.api.services.agent_debug import AgentDebugRunService, get_agent_debug_run_service

router = APIRouter(prefix="/debug/agent-runs", tags=["debug"])


@router.get("/fixtures", response_model=ApiResponse[list[AgentDebugFixtureSummary]])
def list_agent_debug_fixtures(
    service: AgentDebugRunService = Depends(get_agent_debug_run_service),
) -> ApiResponse[list[AgentDebugFixtureSummary]]:
    return ApiResponse.success(service.list_fixtures())


@router.post(
    "/fixtures/{fixture_id}/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Server-sent AgentRunEvent stream.",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "description": "SSE frames using event type as the event name and AgentDebugSseEvent JSON as data.",
                    }
                }
            },
        }
    },
)
def stream_agent_debug_fixture(
    fixture_id: str,
    request: AgentDebugRunRequest,
    service: AgentDebugRunService = Depends(get_agent_debug_run_service),
) -> StreamingResponse:
    return StreamingResponse(
        service.open_fixture_stream(fixture_id=fixture_id, request=request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
