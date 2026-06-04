## Context

`apps/api` 已有 `/api/v1/debug/*` 路由，并通过 `register_api_v1_routes(app, settings)` 在非 production 环境注册。production OpenAPI 已有测试断言不暴露 debug route。`packages/agent` 已提供 `AgentRuntime.run_stream` 和半导体 NVDA fixture scripted harness，可以在无外部 key 情况下产出 run/todo/tool/subagent/artifact/output/completed 事件。

本 change 只为 Web debug chat 提供调试传输层，不定义正式生产 AgentRun API。SSE 是 MVP 推荐：单向、低实现成本、适合“启动一次 run 并看事件流”的页面。

## Goals / Non-Goals

**Goals:**

- 非 production 环境提供可启动 NVDA fixture 的 SSE endpoint。
- production 环境不注册该 endpoint，OpenAPI 不暴露。
- Router 保持薄层：接收 DTO、调用 service、返回 `StreamingResponse`。
- Service 负责 fixture registry、runtime request 构造、stream event 转换、失败事件和断连处理。
- SSE payload 使用小 JSON，字段来自稳定 `AgentRunEvent`，不暴露 secret、完整 prompt、CoT、provider raw response 或 traceback。
- API 测试覆盖 development 可流式读取事件、production 不注册、OpenAPI gating 和失败事件脱敏。

**Non-Goals:**

- 不实现正式 AgentRun persistence、审计 replay、run history 查询或生产 dashboard。
- 不实现 WebSocket topic 通道。
- 不让客户端传任意 prompt、任意 tool 或任意行业包路径。
- 不接真实模型、Tavily、账户、通知、审批或 broker。

## Decisions

### 1. Endpoint 使用 POST + SSE

建议 endpoint：

```text
POST /api/v1/debug/agent-runs/fixtures/{fixture_id}/stream
Content-Type: application/json
Accept: text/event-stream
```

MVP 只支持 `fixture_id=semiconductor-nvda-earnings`，request body 指定：

```python
scenario: Literal["primary", "media_follow_up"]
```

POST 适合“启动一次 run”的语义，也便于后续扩展 debug 参数。启动前 fixture 不存在或请求非法时返回常规 API envelope 4xx；启动后 runtime 错误通过 SSE `run.failed` 事件表达。

### 2. SSE event 格式稳定化

每个 `AgentRunEvent` 转换为：

```text
event: <event.type>
id: <event.event_id>
data: {"event_id": "...", "agent_run_id": "...", "type": "...", "seq": 1, "created_at": "...", "payload": {...}, "safe_summary": "...", "trace_id": "..."}

```

heartbeat 可选，MVP 不要求定时心跳。SSE adapter 必须只序列化 JSON-safe 字段，不直接 dump Python 对象。`data` 中 `payload` 仍保持小对象；大产物只用 artifact id 和 safe summary。

### 3. Router / Service 分层

目标文件规划：

```text
apps/api/src/quantagent/api/
  schemas/agent_debug.py
  services/agent_debug.py
  routers/v1/agent_debug.py
```

Router：

- path / body 参数校验
- 注入 `AgentDebugRunService`
- 返回 `StreamingResponse(media_type="text/event-stream")`

Service：

- 校验 fixture id
- 构造 `AgentRuntime` 和 NVDA fixture request
- 调用 `run_stream`
- 将 `AgentRunEvent` 转换为 SSE frame
- 捕获启动后异常并输出脱敏 `run.failed`

Fixture registry 可以先是 API service 内的常量映射，因为 MVP 只有一个 debug fixture；后续如需复用，再下沉到 package 或核心 registry。API 层不得直接 import 半导体插件内部业务逻辑；只调用 `packages/agent.testing` 提供的公开 fixture helper。

### 4. Production gating 复用既有 debug router 策略

`register_api_v1_routes` 已在 `if not app_settings.is_production` 下注册 debug router。本 change 应把 agent debug route 纳入同一非生产 debug 注册路径。production 下：

- endpoint 返回 404
- `/openapi.json` 不包含该 path
- 不进入 public allowlist

### 5. 断线、超时和失败

MVP 断线处理可依赖 Starlette/FastAPI generator cancellation：捕获 `asyncio.CancelledError` 后停止迭代并允许请求结束，不写入数据库状态。runtime 内部失败时应产生 `run.failed`；service 兜底异常时也输出脱敏 failure frame。

timeout 可先使用 `AgentRuntime` / request policy 后续配置；本 change 不新增生产级 cancellation token。

## Risks / Trade-offs

- [Risk] Debug endpoint 被误认为生产 Agent API。→ Mitigation：只在非 production 注册，OpenAPI production 测试覆盖，README/PR 说明明确非目标。
- [Risk] Router 变厚。→ Mitigation：fixture registry、runtime 调用和 SSE frame 都进 service，router 只返回 StreamingResponse。
- [Risk] SSE payload 泄露 prompt 或 secret。→ Mitigation：只序列化 `AgentRunEvent.safe_summary` 和小 payload，测试注入敏感异常并断言输出不含原文。
- [Risk] Web 后续需要更细 token streaming。→ Mitigation：MVP 保持 AgentRunEvent 粒度；DeepAgents raw chunk 到稳定 event 的转换仍在 `packages/agent`。
- [Risk] API import `packages/agent.testing` 看起来像测试代码进入运行时。→ Mitigation：该 endpoint 是 development-only debug harness；正式 Agent API 后续不得复用 testing helper 作为生产路径。

## Migration Plan

1. 合并 OpenSpec-only PR。
2. 实现 API schemas/service/router，并注册到非 production debug routes。
3. 补 API tests 覆盖 SSE、OpenAPI gating 和脱敏。
4. 运行 `cd apps/api && uv run python -m unittest discover -s src` 或等价命令；同时运行相关 agent tests 确认 fixture helper 仍可用。
5. 安排 SubAgent CR，重点检查 router/service 分层、production exclusion、SSE 安全和 runtime 边界。
