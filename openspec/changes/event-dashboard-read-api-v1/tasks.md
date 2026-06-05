## 1. OpenSpec Review Gate

- [x] 1.1 提交 OpenSpec-only PR。输入：issue #175、proposal、design、spec。输出：只包含 `openspec/changes/event-dashboard-read-api-v1/**` 的 PR。写入边界：OpenSpec artifacts。依赖：无。验证：`openspec validate event-dashboard-read-api-v1 --type change --strict --json`。
- [ ] 1.2 等待维护者明确评论“没问题”或批准后再进入实现代码。输入：OpenSpec-only PR review。输出：可实施的 core/API 实现范围确认。写入边界：无实现代码。依赖：1.1。

## 2. Blocking Contract And Persistence Path

- [x] 2.1 固化标准 Event V1 字段、受控枚举和幂等 identity。输入：design Decisions 2/3/4、spec Event requirements。输出：Event read model 字段、`identity_kind` / `identity_value`、`version`、`current_status`、`analysis_status`、`credibility`、`source_type`、`risk_level`、`risk_direction`、sort mode、section status 的实现前契约清单；不得把 identity 或枚举留到 router 或前端临场发明。写入边界：实现阶段 core model / API schema。依赖：1.2。
- [x] 2.2 新增 `events` 与 `event_state_transitions` ORM 和 migration。输入：2.1 字段清单。输出：SQLAlchemy ORM、Alembic migration、索引、`identity_kind` / `identity_value` unique、非空 `raw_event_id` / `routed_event_id` partial unique 或等价唯一约束、append-only transition schema。写入边界：`packages/core/src/quantagent/core/db/models/*`、`packages/core/alembic/versions/*`。依赖：2.1。验证：migration import、数据库可用时 upgrade / downgrade。
- [x] 2.3 建立 Event repository Protocol 与 SQLAlchemy repository。输入：2.2 schema、query params、summary buckets。输出：list/detail/featured/buckets/state transitions 查询方法，分页和排序在 repository 中稳定实现；upsert 唯一冲突后重读既有 Event；状态更新使用 row lock、version 条件更新或等价机制串行化。写入边界：`packages/core/src/quantagent/core/event_read_model/*`、`packages/core/src/quantagent/core/db/repositories/*`。依赖：2.2。
- [x] 2.4 建立 Event materializer seam。输入：RawEvent、`event_intake` routed-event、analysis summary、approval ref、runtime refs、稳定 identity。输出：幂等 upsert `events`、append `event_state_transitions`、重复输入 no-op 或返回既有 transition、返回 materialization result；提供可测试 service seam，不新增 worker / scheduler loop，不做历史 backfill。写入边界：`packages/core/src/quantagent/core/event_read_model/materializer.py` 或等价职责文件。依赖：2.3。
- [x] 2.5 建立 Event read model service。输入：2.3 repository、2.4 materializer 输出语义。输出：Events list、Event detail、Dashboard featured events、entry metrics、状态摘要和受控降级模型。写入边界：`packages/core/src/quantagent/core/event_read_model/*`。依赖：2.3；若 service 需要复用 materializer result 类型则依赖 2.4。

## 3. Parallel API And Aggregation Slices

- [x] 3.1 API Events DTO 与 router skeleton。输入：2.1 契约清单、spec Events requirements。输出：`schemas/events.py`、`routers/v1/events.py`、response_model、query DTO、OpenAPI tags；query wire shape 固定 `time_range=today|24h|7d|30d`、repeated `industry`、`limit` 默认 20 最大 100。写入边界：`apps/api/src/quantagent/api/schemas/events.py`、`apps/api/src/quantagent/api/routers/v1/events.py`。依赖：2.1；接通真实 service 依赖 2.5。
- [x] 3.2 API Dashboard DTO 与 router skeleton。输入：design Dashboard section 草案、spec Dashboard requirements。输出：`schemas/dashboard.py`、`routers/v1/dashboard.py`、section status DTO、OpenAPI tags。写入边界：`apps/api/src/quantagent/api/schemas/dashboard.py`、`apps/api/src/quantagent/api/routers/v1/dashboard.py`。依赖：2.1；接通真实 service 依赖 2.5。
- [x] 3.3 API service seam。输入：2.5 core service、3.1/3.2 DTO、现有 Approval / Runtime / AgentRun / ToolInvocation 查询入口。输出：`event_api.py` 与 `dashboard_api.py`，负责请求级 Session 组装、core read model 到 API DTO 映射、分区 unavailable / error 归一化；认证和请求校验成功后的局部分区失败返回 HTTP 200 + `ApiResponse.success`，失败只体现在 section status / reason。写入边界：`apps/api/src/quantagent/api/services/*`。依赖：2.5、3.1、3.2。
- [x] 3.4 API v1 protected registration。输入：3.1/3.2 router。输出：Events 与 Dashboard routers 通过 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 注册 protected routes。写入边界：`apps/api/src/quantagent/api/routers/v1/register.py`。依赖：3.1、3.2。

## 4. Integration And Boundary Reviews

- [x] 4.1 Core + API 集成。输入：2.5 core service、3.3 API service、3.4 registration。输出：`GET /api/v1/events`、`GET /api/v1/events/{event_id}`、`GET /api/v1/dashboard/summary` 可通过认证 actor 返回 `ApiResponse[T]`。写入边界：core exports、API services / routers。依赖：2.5、3.3、3.4。
- [x] 4.2 持久化 review checkpoint。输入：2.2/2.3 diff。输出：确认 `event_state_transitions` append-only、ORM/domain/API DTO 分层、查询有 WHERE / LIMIT / 索引、repository 不承载业务规则。依赖：2.3。验证：对照 `core-and-plugin-architecture-gate.md`。
- [x] 4.3 API boundary review checkpoint。输入：3.1/3.2/3.3/4.1 diff。输出：确认 router 不直接查 ORM、不计算评分、不做状态流转、不拼 Dashboard 业务聚合。依赖：4.1。验证：对照 `api-architecture-gate.md`。
- [x] 4.4 Risk boundary review checkpoint。输入：4.1 diff 与 API schema。输出：确认 best_action 只返回摘要 + approval_ref，评分字段不暗示执行通过率或交易授权，不暴露 secret、prompt、provider raw response 或 broker credential。依赖：4.1。

## 5. Tests And Documentation

- [x] 5.1 Core tests。输入：2.2-2.5。输出：覆盖 Event materialization seam、稳定 identity 重复 materialize、唯一冲突重读、重复状态 no-op、并发状态更新串行化或乐观锁重试、Event list/detail、featured sorting、summary buckets、未知事件、append-only state transition、repository pagination、JSON 摘要脱敏边界。写入边界：`packages/core/tests/*`。依赖：2.5。验证：`cd packages/core && uv run python -m unittest discover -s tests`。
- [x] 5.2 API runtime tests。输入：4.1。输出：覆盖 401 protected boundary、200 list/detail/dashboard、404 unknown event、request_id、query params、section `ok` / `empty` / `unavailable` / `error`、局部分区失败仍为 HTTP 200 + 成功 envelope、OpenAPI envelope。写入边界：`apps/api/src/tests/*`。依赖：4.1。验证：`cd apps/api && uv run python -m unittest discover -s src`。
- [x] 5.3 README / usage note。输入：实现后的 route、core read model 边界和验证结果。输出：更新 `apps/api/README.md` 与 core Event read model README 或等价 usage note；不更新 Web feature README。写入边界：API/core 文档。依赖：4.1。
- [x] 5.4 Migration validation。输入：2.2 migration。输出：数据库可用时验证 upgrade / downgrade；不可用时在 PR 中说明原因。依赖：2.2。命令：`uv run quantagent-db upgrade`、`uv run quantagent-db downgrade -1`。

## 6. Final Validation And PR Readiness

- [x] 6.1 OpenSpec validation。输入：任意 OpenSpec artifact 修改。输出：strict validate 通过。命令：`openspec validate event-dashboard-read-api-v1 --type change --strict --json`。
- [ ] 6.2 后端验证汇总。输入：5.1、5.2、5.4。输出：PR 说明列出实际运行命令、结果、未验证项和原因。依赖：5.1、5.2、5.4。
- [ ] 6.3 实现 PR 证据链。输入：issue #175、OpenSpec change、设计文档、测试结果。输出：PR 说明写清为什么新增标准 Event read model、如何复用 RawEvent / routed-event / Approval / Runtime、非目标、风险边界和后续 Web issue。依赖：6.2。

## 7. Optional Parallelization

- [ ] 7.1 可并行切片：2.1 字段契约稳定后，3.1 Events API DTO / router skeleton、3.2 Dashboard API DTO / router skeleton 可以并行起草，但只能返回受控错误或待接通 service，不得使用 mock/sample 冒充真实数据。
- [ ] 7.2 可并行切片：2.3 repository 稳定后，2.4 materializer seam 与 2.5 read service 可以拆给不同执行者，但写入边界必须分别限定在 materializer 与 query service，合并点统一由 4.1 处理。
- [ ] 7.3 不建议并行切片：2.1-2.3 必须单 owner 串行推进，因为字段契约、migration、repository 查询语义互相依赖。
