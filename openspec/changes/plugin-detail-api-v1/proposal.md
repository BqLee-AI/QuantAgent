## 背景

Plugin Registry V1 已经收住了插件列表、最小详情、配置 schema 查询和 rescan 的只读入口，但 `docs/prd/pages/11-plugin-detail.md` 要求的插件治理页并不只是把 Registry 记录原样展开。围绕 `Overview / Config / Dependencies / Capabilities / Health / Audit / Ops` 的七个子域，如果不先定义长期契约，后续前端、API 和 runtime 很容易各自发明 detail payload，并把 secret、绝对路径、runtime 私有错误或 SourceBinding 等其他对象边界混进插件详情资源。

issue #223 的目标不是实现业务代码，而是先把 Plugin Detail V1 的契约、脱敏边界、summary 与子资源分层、future action 挂点，以及与 #117、#219、#220、#226 的职责边界收成一套可审查的 OpenSpec change。

## 本次改动

- 定义 `plugin-detail-api-v1` 能力，收住插件详情主资源和受控子资源的 REST 契约。
- 明确主详情响应必须围绕 `overview`、`config_summary`、`dependency_summary`、`capabilities`、`health_summary`、`audit_summary`、`ops_summary`、`allowed_actions` 组织，而不是继续扩写 Registry V1 的最小 `PluginRecord` DTO。
- 明确 `GET /api/v1/plugins/{plugin_id}/config`、`/dependencies`、`/health`、`/audit` 的职责边界，并为 future `actions/*` 路径预留衔接方式。
- 明确 secret-bearing config、entrypoint、绝对路径、runtime 私有错误和审计敏感字段的脱敏规则。
- 明确 unavailable / not_collected / forbidden 等退化语义，避免实现期只能返回语义不清的 `null`。
- 明确该 change 不覆盖 SourceBinding、SchedulerRun、完整 runtime inspect timeline、配置保存或任何插件写操作实现。

## 非目标

- 不实现 `enable` / `disable` / `reload` / `uninstall` / `save config` / `rescan` 等业务代码。
- 不定义 SourceBinding、SchedulerRun、runtime 全局错误面板或 marketplace 的资源契约。
- 不暴露 `plugin.yaml` 原文、secret 明文、entrypoint 细节、绝对路径、内部栈信息或未治理的私有 metadata。
- 不把 plugin detail API 改成前端专属拼装接口；主资源与子资源都必须复用 API 薄层和 core/plugin 边界。

## 关联真源

- issue: #223
- 相关 issue: #117、#219、#220、#226
- 设计文档: `docs/design/08-api-and-websocket-design.md`
- 前端架构: `docs/design/09-frontend-architecture-design.md`
- PRD: `docs/prd/pages/10-plugins-index.md`、`docs/prd/pages/11-plugin-detail.md`
- 现有 OpenSpec 基线: `openspec/changes/plugin-registry-v1/`

## 影响

- `apps/api` 后续实现需要在薄 router 下暴露主详情与子资源，不再把 Registry 最小记录直接当成最终插件详情。
- `packages/core` / 插件 runtime 后续需要提供插件为中心的 summary read model，但不能把内部 record、audit ORM 或 runtime 错误对象直接回传给 API。
- `apps/web` 后续可以围绕稳定的详情契约构建 `/plugins/:pluginId`，而不是自行拼接页面私有协议。
