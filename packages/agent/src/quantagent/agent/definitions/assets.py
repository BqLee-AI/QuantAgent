from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quantagent.agent.definitions.models import AgentDefinition, SubAgentDefinition
from quantagent.agent.tools.profiles import ToolProfile


def load_agent_assets_from_directory(agent_dir: Path | str) -> tuple[AgentDefinition, ToolProfile, dict[str, ToolProfile]]:
    """从行业包资产目录读取 definition；插件仍只声明资产，runtime 负责执行。"""

    base_dir = Path(agent_dir)
    raw_agent = _read_json(base_dir / "main.json")
    main_prompt = _read_text(base_dir / str(raw_agent.pop("system_prompt_path")))
    main_tool_profile = _load_tool_profile(base_dir / str(raw_agent.pop("tool_profile_path")))

    subagents: list[SubAgentDefinition] = []
    subagent_profiles: dict[str, ToolProfile] = {}
    for item in raw_agent.pop("subagents", []):
        subagent_path = base_dir / str(item["definition_path"])
        raw_subagent = _read_json(subagent_path)
        subagent_prompt = _read_text(subagent_path.parent / str(raw_subagent.pop("system_prompt_path")))
        subagent_profile = _load_tool_profile(subagent_path.parent / str(raw_subagent.pop("tool_profile_path")))
        subagent = SubAgentDefinition(
            **_normalize_skill_paths(base_dir, raw_subagent),
            system_prompt=subagent_prompt,
            tool_ids=[binding.tool_id for binding in subagent_profile.tool_bindings],
        )
        subagents.append(subagent)
        subagent_profiles[subagent.subagent_id] = subagent_profile

    agent = AgentDefinition(
        **_normalize_skill_paths(base_dir, raw_agent),
        system_prompt=main_prompt,
        tool_ids=[binding.tool_id for binding in main_tool_profile.tool_bindings],
        subagents=subagents,
    )
    return agent, main_tool_profile, subagent_profiles


def _load_tool_profile(path: Path) -> ToolProfile:
    return ToolProfile.model_validate(_read_json(path))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"asset must be a JSON object: {path.name}")
    return dict(payload)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _normalize_skill_paths(base_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["skill_paths"] = [
        str((base_dir.parent / skill_path).resolve())
        for skill_path in normalized.get("skill_paths", [])
    ]
    return normalized
