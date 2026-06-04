from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from quantagent.agent.runtime import AgentRuntime
from quantagent.agent.streaming.events import AgentRunEvent, AgentRunEventType
from quantagent.agent.testing import build_nvda_earnings_run_request, build_semiconductor_scripted_runner
from quantagent.api.http.errors import BadRequestError
from quantagent.api.schemas.agent_debug import AgentDebugFixtureSummary, AgentDebugRunRequest, AgentDebugSseEvent

NVDA_EARNINGS_FIXTURE_ID = "semiconductor-nvda-earnings"


@dataclass(frozen=True)
class AgentDebugFixture:
    fixture_id: str
    name: str
    description: str
    scenarios: tuple[str, ...]


class AgentDebugRunService:
    def __init__(self, *, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path(__file__).resolve().parents[6]
        self._fixtures = {
            NVDA_EARNINGS_FIXTURE_ID: AgentDebugFixture(
                fixture_id=NVDA_EARNINGS_FIXTURE_ID,
                name="Semiconductor NVDA earnings chain",
                description="Runs the semiconductor MainAgent NVDA earnings primary/follow-up fixture.",
                scenarios=("primary", "media_follow_up"),
            )
        }

    def list_fixtures(self) -> list[AgentDebugFixtureSummary]:
        return [
            AgentDebugFixtureSummary(
                fixture_id=fixture.fixture_id,
                name=fixture.name,
                description=fixture.description,
                scenarios=list(fixture.scenarios),
            )
            for fixture in self._fixtures.values()
        ]

    def open_fixture_stream(self, *, fixture_id: str, request: AgentDebugRunRequest) -> AsyncIterator[str]:
        fixture = self._fixtures.get(fixture_id)
        if fixture is None:
            raise BadRequestError("未知 Agent debug fixture")
        if request.scenario not in fixture.scenarios:
            raise BadRequestError("不支持的 Agent debug fixture scenario")
        return self.stream_fixture_run(fixture_id=fixture_id, request=request)

    async def stream_fixture_run(
        self,
        *,
        fixture_id: str,
        request: AgentDebugRunRequest,
    ) -> AsyncIterator[str]:
        try:
            runtime = AgentRuntime(scripted_runner=build_semiconductor_scripted_runner())
            run_request = build_nvda_earnings_run_request(
                repo_root=self._repo_root,
                scenario=_scenario_to_fixture_input(request.scenario),
            )
            async for event in runtime.run_stream(run_request):
                yield encode_sse_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            yield encode_sse_event(_safe_failed_event(f"debug_{fixture_id}", "trace_debug_agent_failed", exc))


def get_agent_debug_run_service() -> AgentDebugRunService:
    return AgentDebugRunService()


def encode_sse_event(event: AgentRunEvent) -> str:
    dto = AgentDebugSseEvent(
        event_id=event.event_id,
        agent_run_id=event.agent_run_id,
        type=str(event.type),
        seq=event.seq,
        created_at=event.created_at,
        payload=event.payload,
        safe_summary=event.safe_summary,
        trace_id=event.trace_id,
    )
    data = dto.model_dump(mode="json")
    return f"event: {dto.type}\nid: {dto.event_id}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _scenario_to_fixture_input(scenario: str) -> Literal["primary", "media_follow_up"]:
    if scenario == "media_follow_up":
        return "media_follow_up"
    return "primary"


def _safe_failed_event(agent_run_id: str, trace_id: str, exc: Exception) -> AgentRunEvent:
    return AgentRunEvent(
        agent_run_id=agent_run_id,
        type=AgentRunEventType.RUN_FAILED,
        seq=1,
        payload={"error": f"{type(exc).__name__}: debug agent stream failed"},
        safe_summary="Debug AgentRun stream failed.",
        trace_id=trace_id,
    )
