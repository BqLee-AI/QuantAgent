from __future__ import annotations

from quantagent.plugin_sdk import BasePlugin, PluginInvokeResult


class SemiconductorIndustryPlugin(BasePlugin):
    async def invoke(self, request):
        # 这个占位实现只表达行业包资产已存在；真实分析链路后续通过 AgentRuntime 接入。
        return PluginInvokeResult(
            output={
                "industry": "semiconductor",
                "capability": request.capability,
                "status": "placeholder",
            }
        )


plugin = SemiconductorIndustryPlugin
