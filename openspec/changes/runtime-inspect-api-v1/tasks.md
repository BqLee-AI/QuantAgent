## 1. OpenSpec 审核门槛

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `runtime-inspect-api-v1` 的 proposal、design、tasks、specs 和必要说明。
- [ ] 1.2 在 PR 说明中明确本 PR 只定义 Runtime Inspect V1 只读契约，不实现 runtime / scheduler / API 业务代码。
- [ ] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. 资源与字段契约

- [ ] 2.1 定义 `GET /api/v1/runtime/health` 的摘要字段和 degraded / unavailable 语义。
- [ ] 2.2 定义 `GET /api/v1/agents/runs`、`GET /api/v1/agents/runs/{run_id}` 的 summary/detail 字段与过滤维度。
- [ ] 2.3 定义 `GET /api/v1/tools/invocations`、`GET /api/v1/tools/invocations/{invocation_id}` 的 summary/detail 字段与过滤维度。
- [ ] 2.4 定义 `GET /api/v1/scheduler-runs`、`GET /api/v1/scheduler-runs/{run_id}` 的 runtime 观察子集字段，并与后续 SchedulerRun 契约保持命名一致。
- [ ] 2.5 定义 `GET /api/v1/runtime/errors`、`GET /api/v1/runtime/errors/{error_id}` 的 summary/detail 字段与 severity 过滤。

## 3. 共享过滤、关联和安全边界

- [ ] 3.1 收口共享过滤维度：`event_id`、`trace_id`、`plugin_id`、`status`、`time_from`、`time_to`。
- [ ] 3.2 收口共享关联字段：`request_id`、`correlation_id`、`agent_run_id`、`scheduler_run_id`。
- [ ] 3.3 收口脱敏边界，明确 `summary` 与 `raw` 的区别，V1 不开放 raw。
- [ ] 3.4 收口 empty、error、unavailable 的区分，避免前端和 API 对局部失败理解不一致。

## 4. 后续实现落点

- [ ] 4.1 在 `apps/api` 保持薄 router，只处理 request DTO、response envelope、状态码和 DI。
- [ ] 4.2 在 `apps/api` 或共享 runtime package 中实现 inspect read service / repository seam，不把查询逻辑塞进 router。
- [ ] 4.3 让 `RuntimeHealthSummary`、`AgentRun`、`ToolInvocation`、`SchedulerRun`、`RuntimeError` 的 API DTO 独立于 ORM 或 provider 内部对象。
- [ ] 4.4 与 issue #218 和 issue #226 对齐 query/filter/field naming，避免前端或 scheduler 契约重复造型。

## 5. 验证

- [ ] 5.1 运行 `openspec validate runtime-inspect-api-v1 --type change --strict --json`。
- [ ] 5.2 后续实现 PR 至少验证 list/detail 资源的成功响应 envelope 与 OpenAPI 契约。
- [ ] 5.3 后续实现 PR 至少验证共享过滤维度和资源特定过滤维度。
- [ ] 5.4 后续实现 PR 至少验证 `404`、`401`、`403`、provider unavailable 与 degraded health 语义。
- [ ] 5.5 后续实现 PR 至少验证脱敏断言：不返回 raw prompt、secret、原始敏感参数和 provider 原始异常。
