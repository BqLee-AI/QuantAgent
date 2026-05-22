# 09. 前端架构设计

## 文档状态

**状态**：正式草案 v0.2  
**范围**：React + Vite 前端架构、路由、状态管理、API client、实时事件合并、插件配置表单、HITL 授权交互、运行时可观测 UI、组件体系  
**当前约定**：前端使用 React + Vite + bun；路由使用 TanStack Router；服务端状态使用 TanStack Query；UI 基础库使用 HeroUI v3；后端 API 返回 `code/data/msg/error`；实时通道初版使用 Native WebSocket + topic envelope  
**不包含**：具体 UI 视觉稿、完整页面原型、交易图表系统、移动端 App、第三方插件自定义前端代码

## 设计原则

- 前端定位为运行时管理台 + 审批工作台，不是完整交易终端。
- 前端不承载核心交易判断，不直接绕过后端 Policy Gate。
- REST API 是业务状态真源，实时通道只做增量提醒。
- 前端通过 `packages/contracts/generated/typescript` 消费生成的 API client、types 和 Zod schema。
- 插件配置初版只做 schema-driven form，不允许插件注入自定义前端组件。
- Agent run、tool invocation、Skill、插件状态、审批请求和审计摘要都必须可展示。
- 前端只展示结构化运行过程，不展示完整模型推理链。
- 敏感字段、secret、私有策略、prompt 和交易细节必须脱敏展示。

## 前端应用定位

QuantAgent 前端是运行时管理台、事件分析台、插件后台和 HITL 授权工作台。

核心职责：

- 查看事件流和事件详情。
- 查看事件状态流转和关联分析结果。
- 管理插件安装、配置、启停、错误和依赖。
- 查看 Agent run、tool invocation、scheduler run 和 runtime error。
- 管理 Skill Registry 和 Tool Registry 可见状态。
- 处理 HITL 授权，包括普通审批、短线过期审批、紧急授权和一次性授权链接。
- 查看轻量运行统计，例如事件状态分布、Agent run 成功率、插件健康状态。

不作为初版主线：

- 完整交易终端。
- 行情 K 线、订单簿、实时盘口。
- 手动下单快捷操作台。
- 第三方插件自定义前端渲染。

## 应用目录结构

前端采用 routes + features 混合结构。

```text
apps/web/
  src/
    app/
      router.tsx
      providers.tsx
      layouts/
      bootstrap.tsx

    routes/
      events.index.tsx
      events.$eventId.tsx
      runtime.index.tsx
      approvals.index.tsx
      approvals.$approvalId.tsx
      plugins.index.tsx
      plugins.$pluginId.tsx
      settings.index.tsx

    features/
      events/
        api.ts
        queries.ts
        components/
        types.ts
      runtime/
        queries.ts
        components/
      approvals/
        api.ts
        queries.ts
        components/
      plugins/
        api.ts
        queries.ts
        components/
      skills/
      tools/
      industries/

    shared/
      api/
      realtime/
      query/
      forms/
      ui/
      config/
      errors/
      auth/
      utils/
```

规则：

- `routes/` 只负责页面入口、loader、search params 和页面组合。
- `features/` 承载业务模块的 query、mutation、组件和局部类型。
- `shared/` 只放跨模块基础能力，不放业务规则。
- 页面不能直接调用底层 fetch，应通过 feature query / mutation 或 shared api client。
- 生成代码不放入 `features/`，统一从 `packages/contracts/generated/typescript` 引用。

## 路由设计

路由使用 TanStack Router。

原因：

- 事件、审批、Agent run、插件等页面都有复杂筛选、分页和详情路由。
- URL search params 需要稳定、可分享、可恢复。
- 类型安全路由能减少前端参数错误。
- TanStack Router 和 TanStack Query 组合自然。

路由设计规则：

- 列表筛选条件进入 URL search params。
- 详情页使用稳定资源 ID。
- 审批、事件、Agent run 页面可以通过 URL 直接打开。
- 一次性授权链接使用独立 route，避免依赖完整后台布局。
- 不把敏感 token 长期保存在 URL；一次性 link token 校验后应换取短期上下文。

建议初版路由：

```text
/events
/events/:eventId
/runtime
/runtime/agents/:runId
/runtime/tools/:invocationId
/approvals
/approvals/:approvalId
/approval-link/:token
/plugins
/plugins/:pluginId
/skills
/tools
/industries
/settings
```

## 状态管理

服务端状态使用 TanStack Query。React state 处理局部 UI 状态。Zustand 只在确实需要跨页面客户端状态时引入。

服务端状态包括：

- Event。
- Plugin。
- Agent run。
- Tool invocation。
- Skill。
- Approval。
- Notification。
- Audit log。
- Runtime health。

局部 UI 状态包括：

- 弹窗开关。
- 表格展开行。
- 当前 tab。
- 表单草稿。
- 一次性局部选择。

可以考虑 Zustand 的场景：

- 命令面板。
- 全局 dock / layout 状态。
- 跨页面选中上下文。
- 本地 UI 偏好。

规则：

- 不把服务端状态长期复制进 Zustand。
- query key 必须集中定义。
- mutation 成功后必须按资源边界 invalidate。
- WebSocket 消息默认触发 query invalidation。
- 乐观更新只用于低风险 UI 状态，不用于交易授权结果。

## API Client

前端基于 generated client 包一层薄 `apiClient`。

职责：

- 统一 unwrap `ApiResponse<T>`。
- 统一处理 `code/data/msg/error`。
- 统一注入鉴权 token / session。
- 统一处理 401、403、业务错误码和网络错误。
- 统一暴露 `request_id`、`trace_id` 给错误 UI。
- 给 TanStack Query hooks 提供稳定调用入口。

建议结构：

```text
shared/api/
  client.ts
  errors.ts
  envelope.ts
  request-context.ts
```

规则：

- 页面不直接处理后端 envelope。
- 失败时抛出标准 `ApiError`。
- 错误 toast 优先展示 `msg`。
- 详情错误面板展示 `request_id` 和 `trace_id`。
- 生成 client 不手改，只通过生成脚本更新。

## 实时事件合并

实时通道使用 Native WebSocket + topic envelope。前端默认用实时消息触发 TanStack Query invalidation，少量高频运行状态允许局部 patch。

默认规则：

- `event.*` 默认 invalidate event query。
- `approval.*` 默认 invalidate approval query。
- `plugin.*` 默认 invalidate plugin query。
- `runtime.failed` 触发全局 runtime error 提醒，并刷新 runtime query。
- `agent.run.step_added` 可以局部 append 到当前 run timeline。
- `tool.invocation.updated` 可以局部 patch 当前 invocation 状态。

断线恢复：

```text
WebSocket disconnected
  -> show connection degraded state
  -> reconnect
  -> refresh current route critical queries
  -> resume topic subscription
```

规则：

- WebSocket payload 不作为完整业务状态长期保存。
- 页面初始化必须通过 REST 获取快照。
- reconnect 后必须刷新当前页面关键 query。
- 局部 patch 后仍应通过 REST refresh 校准。
- 如果初版实时能力未完成，页面可以先通过 TanStack Query polling 降级。

## 插件配置表单

插件配置表单使用 JSON Schema form。普通业务表单使用 Zod 驱动的常规 React 表单方案。

插件配置表单规则：

- 从 `/plugins/{plugin_id}/config-schema` 获取 schema。
- 从 `/plugins/{plugin_id}/config` 获取当前配置。
- 敏感字段显示 masked value 或 secret reference。
- 提交前调用 validate API。
- 保存成功后刷新插件详情和 audit log。
- 插件不得提供自定义前端组件。
- 后续如需要增强体验，只允许增加受控 uiSchema。

普通业务表单场景：

- 登录或本地 token 输入。
- 审批备注。
- 手动触发 source binding。
- Approval amend。
- 通知渠道测试。

普通业务表单可使用 Zod schema 和 React 表单库实现，不强制走 JSON Schema form。

## UI 组件体系

UI 基础库使用 HeroUI v3。

shadcn 不作为基础 UI 库，只在 HeroUI 缺少特定组件或交互模式时作为补充来源，例如 registry 中的动画组件、特殊 layout 组件或实验性组件。补充组件必须进入本项目的 `shared/ui` 管理，不允许页面随意复制粘贴。

组件策略：

- HeroUI v3 作为按钮、输入框、弹窗、表格、菜单、tabs、toast、tooltip 等基础组件来源。
- 自定义 design tokens 管理色彩、间距、圆角、阴影、动效和风险状态。
- shadcn registry 仅作为补充组件来源，不作为全局设计系统。
- 复杂运行时组件由业务组件实现，例如 Agent timeline、Approval risk panel、Plugin health card。
- 图表和可视化组件单独选择轻量库，不纳入基础 UI 库讨论。

设计 token 需要覆盖：

- 普通状态。
- 成功状态。
- 警告状态。
- 错误状态。
- 高风险 increase_risk。
- 降低风险 reduce_risk。
- 即将过期 approval。
- 已执行后通知 execute_then_notify。

## 核心页面结构

初版页面按运行链路规划，而不是按传统后台 CRUD 菜单规划。

### Event Inbox

职责：

- 展示事件列表。
- 展示事件状态。
- 展示事件来源、捕获时间、实体、标签。
- 支持按状态、行业、来源、时间筛选。
- 从事件进入详情页查看状态流转、关联分析、Decision 和审批请求。

### Runtime

职责：

- 展示 Agent run。
- 展示 tool invocation。
- 展示 scheduler run。
- 展示 runtime error。
- 支持按 trace_id、event_id、status、plugin_id 筛选。

### Approvals

职责：

- 展示待授权、即将过期、已处理、已过期、已自动执行的请求。
- 展示 `expires_at` 倒计时。
- 展示 `expiration_action`。
- 展示风险方向：increase_risk / reduce_risk / neutral。
- 支持 approve、reject、request_reanalysis、amend。
- 支持一次性授权 link 页面。

### Plugins

职责：

- 展示插件列表、类型、版本、状态和来源。
- 支持安装、启用、停用、reload。
- 展示插件配置表单。
- 展示插件依赖、错误和 audit。

### Skills & Tools

职责：

- 展示 Skill Registry。
- 展示 Tool Registry。
- 展示 Tool schema、授权状态、来源插件。
- 展示 Skill 被哪些 Agent 引用。

### Industries

职责：

- 展示行业包。
- 展示 SourceBinding。
- 展示 industry agents、skills、tools 和 market mapping 摘要。
- 展示行业包配置状态和依赖状态。

### Settings

职责：

- 本地鉴权配置。
- 通知渠道配置。
- Secret reference 管理入口。
- 用户授权策略。
- 实时通道状态。

## Agent / Tool / Skill 可观测 UI

Agent run 使用结构化 timeline，不展示完整模型推理链。

Timeline 展示：

- run status。
- started_at / finished_at。
- event_id / trace_id。
- 使用的 AgentDefinition。
- 使用的 Skill 列表。
- 工具调用步骤。
- 每一步耗时。
- 错误摘要。
- 输出摘要。

Tool invocation 展示：

- tool id。
- 来源插件。
- 参数摘要。
- 结果摘要。
- 耗时。
- retry 次数。
- error code。
- trace_id。

Skill 展示：

- skill id。
- 来源：official / industry / runtime / private。
- version。
- 授权状态。
- 被哪些 AgentDefinition 引用。
- `SKILL.md` 摘要。

规则：

- 不展示完整 chain-of-thought。
- Prompt、密钥、私有策略和敏感配置必须脱敏。
- Tool 参数和结果默认摘要展示，用户需要权限才能展开更多细节。
- 从事件详情可以跳转到相关 Agent run 和 tool invocation。

## HITL 授权交互

HITL 采用审批工作台 + 紧急授权浮层 + 一次性授权页。

初版必须支持：

- Approval Inbox 列表。
- Approval Detail 详情。
- `expires_at` 倒计时。
- `expiration_action` 明确展示。
- 风险方向展示：increase_risk / reduce_risk / neutral。
- approve / reject / request_reanalysis / amend。
- 一次性授权 link 页面。
- 高风险操作二次确认。

交互规则：

- 短线过期后按钮自动禁用或触发重新分析。
- `execute_then_notify` 必须清晰显示“已执行后通知”，不能伪装成待审批。
- 对 increase_risk 动作用更强视觉提示和二次确认。
- 对 reduce_risk 动作展示执行依据和用户预授权来源。
- 对 link_confirm 展示链接过期时间和目标 action 摘要。
- 对 manual_only 隐藏文本确认入口，只保留强确认入口。
- Approval amend 必须清晰展示用户修改了哪些参数。

## 前端权限与 Capability

初版只做单用户鉴权 + capability 控制，不做完整 RBAC。

规则：

- 前端基于 `/runtime/health` 或 `/me` 类接口获取 capabilities。
- UI 隐藏不可用入口，但后端仍必须做真正权限校验。
- 插件启停、secret 配置、approval、executor 能力都必须显示权限状态；初版 executor 只做虚盘，不操作实盘。
- 初版虚盘 capability key 仍为 `executor.dry_run`，不因为中文术语改成虚盘而新增前端 capability key。
- 一次性授权 link 页面只展示该 token 允许查看和操作的最小信息。
- 权限不足错误需要展示 `request_id`，方便排查。

Capability 示例：

```text
plugin.install
plugin.configure
approval.approve
approval.amend
executor.dry_run
secret.manage
runtime.inspect
```

## 图表与数据可视化

初版只做运行状态轻量可视化，不做完整交易终端图表。

初版图表范围：

- Event status 分布。
- Agent run 成功率、失败率、耗时。
- Tool invocation 错误趋势。
- Approval 即将过期数量。
- Plugin health 摘要。

暂不进入初版：

- 行情 K 线。
- 订单簿。
- 实时盘口。
- 复杂回测图表。

## 初版落地顺序

建议按以下顺序实现：

1. Vite + React + TanStack Router 基础应用骨架。
2. HeroUI v3、design tokens、基础 layout。
3. generated client 薄封装和 `ApiError` 处理。
4. TanStack Query provider、query key 规范和基础 hooks。
5. Event Inbox 和 Plugin 列表。
6. 插件 JSON Schema form。
7. Runtime timeline：Agent run + tool invocation。
8. Approval Inbox、Approval Detail、一次性授权 link 页面。
9. Native WebSocket topic client 和 query invalidation。
10. 轻量运行状态图表。
