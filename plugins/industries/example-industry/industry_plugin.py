from __future__ import annotations

from quantagent.plugin_sdk import BasePlugin, PluginInvokeResult


class ExampleIndustryPlugin(BasePlugin):
    async def invoke(self, request):
        # 这个样例只证明行业包资产布局，不承担调度、effective config 合成或真实分析执行。
        return PluginInvokeResult(
            output={
                "industry": "example",
                "capability": request.capability,
                "status": "placeholder",
            }
        )


plugin = ExampleIndustryPlugin
