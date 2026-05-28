## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `plugin-scheduling-v1` 的 proposal、design、specs、tasks 和必要说明。
- [x] 1.2 在 PR 说明中写清楚：本 PR 只定义 Plugin Scheduling V1 contract，不实现 core scheduling service、API、worker、数据库迁移或 Event Bus。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. 调度边界与模型

- [x] 2.1 定义 Scheduling V1 与 Registry、Runtime V1、Plugin IO DTO V1 的分层关系。
- [x] 2.2 定义 `PluginTriggerRequest` 的最小字段：`plugin_id`、`capability`、`request_id`、`trigger_type`、`input`、`effective_config`、`metadata`、`timeout_ms`。
- [x] 2.3 定义 `PluginRunRecord` 的最小字段：`run_id`、`plugin_id`、`plugin_version`、`capability`、`request_id`、`trigger_type`、`status`、`started_at`、`finished_at`、`duration_ms`、`timeout_ms`、`output_summary`、`error_summary` 和 `metadata`。
- [x] 2.4 定义 run 状态机：`queued`、`running`、`succeeded`、`failed`、`timeout`、`cancelled`。
- [x] 2.5 定义 JSON-safe、脱敏、不可暴露宿主内部对象的字段边界。

## 3. 手动 trigger 与 interval 范围

- [x] 3.1 定义手动 trigger 的输入、输出、成功和失败场景。
- [x] 3.2 定义 interval policy 的最小边界，确保 interval trigger 复用同一个 scheduling service。
- [x] 3.3 明确 V1 不实现完整分布式 scheduler、复杂 retry/backoff/rate limit/circuit breaker。
- [x] 3.4 明确 API 只能作为薄 trigger 边界，不作为长期 scheduler loop。

## 4. 后续实现落点

- [x] 4.1 在 `packages/core/src/quantagent/core/scheduling/` 中实现 scheduling models、service、repository port 和可注入 clock。
- [x] 4.2 复用 `PluginRuntimeService.invoke`，不在 scheduling service 中重新实现插件加载、生命周期或 capability 分支。
- [x] 4.3 实现最小内存 run repository 作为 contract test harness；如需数据库持久化，另行评估迁移边界。
- [x] 4.4 本轮不实现 API trigger；如后续需要 API trigger，保持 `apps/api` router 薄层，只调用 core scheduling service。

## 5. 验证

- [x] 5.1 运行 `openspec validate plugin-scheduling-v1 --type change --strict --json`。
- [x] 5.2 后续实现 PR 至少验证手动 trigger 成功 run：状态、时间字段、duration_ms 和 output_summary。
- [x] 5.3 后续实现 PR 至少验证 Runtime 结构化失败 run：`failed` 状态和脱敏 error_summary。
- [x] 5.4 后续实现 PR 至少验证 timeout run：`timeout` 状态、timeout_ms、timeout error_summary、finished_at 和 duration_ms。
- [x] 5.5 后续实现 PR 至少验证空结果 run：`succeeded` 状态与空 output_summary 可区分。
- [x] 5.6 后续实现 PR 至少验证 interval policy 构造 `trigger_type=interval` 的 trigger request。
