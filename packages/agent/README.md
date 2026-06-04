# QuantAgent Agent Runtime

`packages/agent` 是 QuantAgent 运行 DeepAgents 的统一基础设施。行业包、API service、Worker 和测试 fixture 应通过 `AgentRuntime` 启动 Agent run，不直接创建 DeepAgents 实例。

## 职责

- 解析和承载 `AgentDefinition`、`SubAgentDefinition`、`ToolProfile`、`RuntimePolicy` 等通用契约。
- 调用 DeepAgents `create_deep_agent()`，并把工具、SubAgent、skills、backend、interrupt policy 和 checkpointer 作为配置传入。
- 为工具注入 run-scoped hidden context，例如 `agent_run_id`、`event_id`、`trace_id` 和 `tool_profile_id`。
- 管理当前 run 的 artifact 引用，优先通过 `artifact_id` 和 `safe_summary` 传递大产物。
- 将运行过程转换成稳定的 `AgentRunEvent` 流，供 API SSE 或其他调试入口消费。

## 子目录

- `definitions/`：Agent 和 SubAgent 定义、runtime policy、定义加载器。
- `runtime/`：`AgentRuntime` 入口、run request/result、run context 和错误类型。
- `tools/`：tool profile、平台工具协议、DeepAgents tool adapter 和调用摘要。
- `artifacts/`：artifact 类型、引用和当前 run 的 in-memory store。
- `streaming/`：稳定事件类型和 DeepAgents/LangGraph chunk adapter。
- `testing/`：无外部模型和 secret 的 fake harness。

## 不负责什么

- 不做 FastAPI router、SSE 编码、Web 类型或 API envelope。
- 不直接发现、加载或执行具体插件实现；插件和 ToolRegistry 的真实治理在 core/plugin 边界。
- 不接真实 broker、真实通知、真实账户或生产交易。
- 不默认保存完整 chain-of-thought、完整 prompt、provider raw response、secret 或私有策略明文。

## DeepAgents 复用边界

`AgentRuntime` 只封装和约束 DeepAgents harness，不重写 planning、tool loop、SubAgent 调度、filesystem backend 或 HITL loop。实现 DeepAgents 相关代码前必须查阅官方文档、examples 和本地安装版本；若文档与本地版本冲突，以可运行测试和 PR 说明中的取舍为准。

## 最小用法

```python
from quantagent.agent.runtime import AgentRuntime
from quantagent.agent.testing.fixtures import build_echo_run_request

runtime = AgentRuntime()
request = build_echo_run_request()

async for event in runtime.run_stream(request):
    print(event.type, event.safe_summary)
```
