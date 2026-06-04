from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from quantagent.agent.definitions.assets import load_agent_assets_from_directory
from quantagent.agent.definitions.models import AgentDefinition, RuntimePolicy
from quantagent.agent.runtime.context import RunContextSection, RunContextSnapshot
from quantagent.agent.runtime.requests import AgentRunRequest
from quantagent.agent.tools.profiles import ToolProfile

SEMICONDUCTOR_INDUSTRY_ID = "quantagent.official.industry.semiconductor"
MAIN_AGENT_ID = "quantagent.official.industry.semiconductor.agent.main"
RESEARCH_SUBAGENT_ID = "quantagent.official.industry.semiconductor.subagent.evidence_research_analyst"


@dataclass
class SemiconductorFixtureLedger:
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    subagent_tasks: list[dict[str, Any]] = field(default_factory=list)

    def record_tool(self, name: str, input_data: Mapping[str, Any]) -> None:
        self.tool_calls.append({"name": name, "input": dict(input_data)})

    def count_tool(self, name: str) -> int:
        return sum(1 for call in self.tool_calls if call["name"] == name)


@dataclass(frozen=True)
class SemiconductorAssets:
    agent_definition: AgentDefinition
    main_tool_profile: ToolProfile
    subagent_tool_profiles: dict[str, ToolProfile]


def load_semiconductor_assets(repo_root: Path | str) -> SemiconductorAssets:
    plugin_dir = Path(repo_root) / "plugins" / "industries" / "semiconductor-industry"
    agent_definition, main_profile, subagent_profiles = load_agent_assets_from_directory(plugin_dir / "agents")
    return SemiconductorAssets(
        agent_definition=agent_definition,
        main_tool_profile=main_profile,
        subagent_tool_profiles=subagent_profiles,
    )


def build_nvda_earnings_run_request(
    *,
    repo_root: Path | str,
    scenario: Literal["primary", "media_follow_up"],
) -> AgentRunRequest:
    assets = load_semiconductor_assets(repo_root)
    event_id = "evt_nvda_earnings_release_001" if scenario == "primary" else "evt_nvda_media_beat_001"
    event_summary = (
        "NVIDIA 一手财报公告，包含收入、data center、毛利率和下一季度收入指引。"
        if scenario == "primary"
        else "NVIDIA 财报超预期的二手媒体报道，疑似同一季度财报主题 follow-up。"
    )

    return AgentRunRequest(
        agent_run_id=f"run_nvda_{scenario}",
        event_id=event_id,
        industry_id=SEMICONDUCTOR_INDUSTRY_ID,
        trace_id=f"trace_nvda_{scenario}",
        agent_definition=assets.agent_definition,
        run_context=RunContextSnapshot(
            context_id=f"context_nvda_{scenario}",
            sections=[
                RunContextSection(
                    name="event",
                    summary=event_summary,
                    data={
                        "symbols": ["NVDA"],
                        "issuer": "NVIDIA",
                        "event_family": "quarterly_earnings",
                        "source_tier": "primary" if scenario == "primary" else "secondary",
                    },
                ),
                RunContextSection(
                    name="route_context",
                    summary="Router assigned this event to semiconductor with direct relationship.",
                    data={"owner_id": "semiconductor", "relationship": "direct"},
                ),
                RunContextSection(
                    name="market_mapping",
                    summary="NVDA maps directly to AI GPU and data center accelerator demand.",
                    data={"symbols": ["NVDA", "MU", "TSM", "ASML"]},
                ),
            ],
            safe_summary=f"NVDA {scenario} semiconductor run context.",
        ),
        tool_profile=assets.main_tool_profile,
        runtime_policy=RuntimePolicy(model=None, max_subagent_tasks=1),
        input_message=f"Analyze {event_id} with the semiconductor MainAgent MVP flow.",
    )
