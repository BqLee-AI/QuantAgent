## 1. OpenSpec 评审

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `plugin-detail-api-v1` change 的 proposal、design、tasks、specs 和必要元数据。
- [ ] 1.2 在 PR 说明中明确本 PR 关联 issue #223，且只定义 Plugin Detail V1 契约，不实现任何业务代码。
- [ ] 1.3 等维护者明确评论“没问题”或批准后，再进入 API / core / web 的实现拆分。

## 2. 主详情契约

- [ ] 2.1 定义 `GET /api/v1/plugins/{plugin_id}` 的主详情结构，显式包含 `overview`、`config_summary`、`dependency_summary`、`capabilities`、`health_summary`、`audit_summary`、`ops_summary`、`allowed_actions`、`links`。
- [ ] 2.2 明确主详情复用 Registry V1 的身份字段，但不继续扁平扩写 `PluginRecord` DTO。
- [ ] 2.3 定义主详情的 404、forbidden 和最小可见性语义。

## 3. 子资源与数据边界

- [ ] 3.1 定义 `GET /api/v1/plugins/{plugin_id}/config` 的只读配置契约，明确 schema/value 分层和 secret 脱敏。
- [ ] 3.2 定义 `GET /api/v1/plugins/{plugin_id}/dependencies` 的依赖契约，明确 required/optional、resolved state、reverse dependency 和 blocked reason。
- [ ] 3.3 定义 `GET /api/v1/plugins/{plugin_id}/health` 的插件中心健康契约，明确与 runtime inspect 全局时间线的边界。
- [ ] 3.4 定义 `GET /api/v1/plugins/{plugin_id}/audit` 的最近审计契约，明确 append-only 摘要和敏感字段脱敏。

## 4. 能力、运维与退化语义

- [ ] 4.1 定义 `capabilities` 的最小字段集，明确 risk level、policy gate、approval gate 和 broker 的 `dry_run/mock` 边界。
- [ ] 4.2 定义 `ops_summary`、`allowed_actions` 与 future `actions/*` 路径的衔接方式，不把动作 hint 误当成已实现 mutation。
- [ ] 4.3 定义 `not_collected`、`unavailable`、`forbidden`、`degraded` 等退化语义，避免子域只返回语义不清的 `null`。

## 5. 后续实现 Gate

- [ ] 5.1 在实现前补齐 API DTO、service/read model、Registry/runtime/audit 数据源之间的目录蓝图与职责映射。
- [ ] 5.2 在实现前确认与 #117、#219、#220、#226 的边界，避免把 SourceBinding、SchedulerRun 或列表页语义混入本 change。
- [ ] 5.3 实现 PR 至少验证主详情/子资源契约、脱敏断言、权限拒绝路径和 OpenAPI 契约。
