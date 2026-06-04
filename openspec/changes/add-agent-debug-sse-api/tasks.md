## 1. OpenSpec / 设计确认

- [ ] 1.1 strict validate 本 change。
- [ ] 1.2 OpenSpec-only PR 只包含本 change artifacts。

## 2. API schema / service / router

- [ ] 2.1 新增 `schemas/agent_debug.py`，定义 fixture request、fixture summary 和 SSE event DTO。
- [ ] 2.2 新增 `services/agent_debug.py`，封装 fixture registry、AgentRuntime 调用、SSE frame 序列化和 safe failure frame。
- [ ] 2.3 新增或扩展 debug router，提供 `POST /api/v1/debug/agent-runs/fixtures/{fixture_id}/stream`。
- [ ] 2.4 通过现有 `register_api_v1_routes` 非 production debug gate 注册，不在 production 注册。

## 3. Runtime / fixture 接入

- [ ] 3.1 service 使用 `packages/agent` 公开 fixture helper 启动 `semiconductor-nvda-earnings`，不直接 import 半导体插件内部模块。
- [ ] 3.2 stream 事件来自 `AgentRuntime.run_stream`，router/service 不直接调用 `create_deep_agent()`。
- [ ] 3.3 SSE frame 使用 JSON-safe `AgentRunEvent` 字段，避免 Python repr、secret、prompt、CoT 和 traceback。

## 4. 测试

- [ ] 4.1 API 测试覆盖 development/test 环境可读取 SSE，并断言 `run.started`、中间事件和 `run.completed` 或 `run.failed`。
- [ ] 4.2 API 测试覆盖 production 404 和 production OpenAPI 不包含 debug stream path。
- [ ] 4.3 API 测试覆盖未知 fixture 返回非 streaming envelope 4xx。
- [ ] 4.4 API 或 service 测试覆盖 failure frame 脱敏。

## 5. Review / 验证 / PR

- [ ] 5.1 运行 API unittest 和必要 agent tests。
- [ ] 5.2 运行 `openspec validate add-agent-debug-sse-api --type change --strict --json`。
- [ ] 5.3 安排 SubAgent CR，重点检查 router/service 分层、production exclusion、SSE 安全和 runtime 边界。
- [ ] 5.4 根据 CR 修复后创建实现 PR。
