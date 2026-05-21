## Why

issue #97 已经把前端登录、`/me` 会话恢复、受保护路由和 401/403 基础语义收住，但它明确只做到“capability 状态展示”，没有继续定义 capability policy、路由 guard、导航可见性和统一 403 权限不足体验。issue #106 正是承接这块留白。

现在做这件事，是因为 issue #97 合入后，前端将具备 capability snapshot、统一 auth provider 和集中 API error 边界；如果继续让后续 workspace 页面各自决定“入口该隐藏还是禁用、capability 不足是否跳 `/login`、403 怎么展示 request_id / trace_id”，权限语义会在真实页面接入前先分叉。

## What Changes

- 收住前端 capability policy 的统一落点，使 route guard、navigation hiding / disabling 和页面入口判断消费同一份 policy。
- 为 workspace 路由建立 capability-aware guard，明确“未登录”与“已登录但 capability 不足”是两条不同语义路径。
- 定义首批 navigation / entry / high-risk action 的统一可见性规则，禁止页面组件各自决定隐藏或禁用行为。
- 定义统一 403 权限不足 UX，要求保留并展示 `request_id` / `trace_id` 入口，不泄露 session、password、secret、token 或私有策略原文。
- 本 change 只收前端单用户 capability 控制的 UX 与 guard 边界，不扩展 RBAC、多用户、租户、后端 capability 枚举来源、策略 DSL 或新鉴权服务。

## Capabilities

### New Capabilities
- `web-capability-guard-403-ux`: 定义前端 capability policy、受限路由语义、统一 navigation / action policy 和 403 权限不足体验。

### Modified Capabilities
- `router-layout`: 路由与布局 requirement 从“登录页与受保护后台分离”扩展为“capability 不足时仍走受限路由语义，而不是退回登录语义”。
- `api-client-error-governance`: API error requirement 从“401/403 基础收口”扩展为“403 保留稳定诊断元数据，供统一权限体验消费”。

## Impact

- 前端 shared auth / routing / layout 边界：需要引入统一 capability policy，并让 route guard 与导航状态消费这份 policy。
- 前端 error governance 边界：需要保证 403 的 `request_id` / `trace_id` 元数据能稳定进入统一权限不足体验。
- OpenSpec delta：
  - `specs/web-capability-guard-403-ux/spec.md`
  - `specs/router-layout/spec.md`
  - `specs/api-client-error-governance/spec.md`
