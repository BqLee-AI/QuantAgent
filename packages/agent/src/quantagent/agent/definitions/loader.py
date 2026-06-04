from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quantagent.agent.definitions.models import AgentDefinition


def load_agent_definition_from_mapping(payload: Mapping[str, Any]) -> AgentDefinition:
    """测试和插件适配层的最小入口；Markdown/frontmatter 解析后续再接入。"""

    return AgentDefinition.model_validate(dict(payload))
