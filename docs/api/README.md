# QuantAgent API 文档索引

本文档记录当前 `apps/api` 已注册的 `/api/v1` HTTP API。API 运行时以 FastAPI OpenAPI schema 为机器可读契约；本目录用于前端和评审快速确认路由边界、鉴权要求和模块职责。

## 通用约定

- Base Path: `/api/v1`
- 默认成功响应使用 `code/data/msg/error` envelope。
- 错误响应使用同一 envelope，并在 `error.request_id` 中返回请求 ID。
- protected route 需要有效 session cookie；受保护写操作还需要 `X-CSRF-Token`。
- public route 不需要 session；但 notification ingress 可能有插件级签名或 provider 校验。
- `debug` route 仅在非 production 环境注册，不能作为生产 API 依赖。

## 模块文档

| 模块 | 文档 | 说明 |
| --- | --- | --- |
| Auth | [auth/auth_frontend_routes.md](auth/auth_frontend_routes.md) | 登录、当前用户、刷新 session、登出 |
| Dashboard | [dashboard/dashboard_frontend_routes.md](dashboard/dashboard_frontend_routes.md) | Dashboard 首屏聚合摘要 |
| Events | [events/events_frontend_routes.md](events/events_frontend_routes.md) | 标准事件列表、事件详情和 summary buckets |
| Approval | [approvals/approvals_frontend_routes.md](approvals/approvals_frontend_routes.md) | Approval 队列、详情和 approve / reject / request-reanalysis actions |
| Plugins | [plugins/plugins_frontend_routes.md](plugins/plugins_frontend_routes.md) | 插件列表、详情、配置、依赖、健康、审计和重扫 |
| Source Bindings | [source_bindings/source_bindings_frontend_routes.md](source_bindings/source_bindings_frontend_routes.md) | SourceBinding 列表、详情、关联运行记录和 pause / resume / run-now actions |
| Models | [models/models_frontend_routes.md](models/models_frontend_routes.md) | Model provider、provider model、preset 和 invocation |
| Runtime | [runtime/runtime_frontend_routes.md](runtime/runtime_frontend_routes.md) | Runtime health、Agent run、Tool invocation、Scheduler run、RawEvent 和 audit timeline |
| Wallet | [wallet/wallet_frontend_routes.md](wallet/wallet_frontend_routes.md) | paper wallet 账户、余额、持仓、流水、模拟订单和成交 |
| Cookie / CSRF | [http_cookie/frontend-cookie-session-guide.md](http_cookie/frontend-cookie-session-guide.md) | 前端 Cookie session 接入 |
| Cookie 技术细节 | [http_cookie/http-cookie-technical-guide.md](http_cookie/http-cookie-technical-guide.md) | 后端 Cookie / session / CSRF 技术设计 |

## 当前路由清单

### Public

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 存活探针，不依赖数据库 |
| GET | `/ready` | 数据库 readiness probe |
| GET | `/version` | API 版本信息 |
| POST | `/auth/login` | 本地管理员登录 |
| POST | `/integrations/notifications/ingress` | notification ingress HTTP host；不走统一 envelope |

### Auth Protected

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/me` | 当前 actor 快照与 CSRF token |
| POST | `/auth/refresh` | 刷新 session，需要 CSRF |
| POST | `/auth/logout` | 登出，需要 CSRF |

### Approvals

| 方法 | 路径 | Capability | CSRF | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/approvals` | `approval.read` | 否 | Approval 队列 |
| GET | `/approvals/{approval_id}` | `approval.read` | 否 | Approval 详情和 history |
| POST | `/approvals/{approval_id}/actions/approve` | `approval.approve` | 是 | 记录 approve 输入并进入 evaluator / Policy Gate |
| POST | `/approvals/{approval_id}/actions/reject` | `approval.approve` | 是 | 记录 reject 输入并终止审批 |
| POST | `/approvals/{approval_id}/actions/request-reanalysis` | `approval.approve` | 是 | 只记录重分析意图，不触发 runtime |

### Plugins

| 方法 | 路径 | CSRF | 说明 |
| --- | --- | --- | --- |
| GET | `/plugins` | 否 | 插件列表 |
| GET | `/plugins/{plugin_id}` | 否 | 插件详情聚合视图 |
| GET | `/plugins/{plugin_id}/config` | 否 | 配置只读视图 |
| GET | `/plugins/{plugin_id}/dependencies` | 否 | 依赖视图 |
| GET | `/plugins/{plugin_id}/health` | 否 | 健康摘要 |
| GET | `/plugins/{plugin_id}/audit` | 否 | 审计摘要 |
| GET | `/plugins/{plugin_id}/config-schema` | 否 | manifest 配置 JSON Schema |
| POST | `/plugins/actions/rescan` | 是 | 重新扫描插件目录 |

### Source Bindings

| 方法 | 路径 | Capability | CSRF | 说明 |
| --- | --- | --- | --- | --- |
| GET | `/source-bindings` | `source_binding.read` | 否 | SourceBinding 列表 |
| GET | `/source-bindings/{binding_id}` | `source_binding.read` | 否 | SourceBinding 详情 |
| GET | `/source-bindings/{binding_id}/scheduler-runs` | `source_binding.read` | 否 | 关联 scheduler runs |
| POST | `/source-bindings/{binding_id}/actions/pause` | `source_binding.control` | 是 | 暂停 binding |
| POST | `/source-bindings/{binding_id}/actions/resume` | `source_binding.control` | 是 | 恢复 binding |
| POST | `/source-bindings/{binding_id}/actions/run-now` | `source_binding.control` | 是 | 立即触发一次运行 |

### Models

| 方法 | 路径 | CSRF | 说明 |
| --- | --- | --- | --- |
| GET | `/models/providers` | 否 | Model provider 列表 |
| POST | `/models/providers` | 是 | 创建 provider |
| GET | `/models/providers/{provider_id}` | 否 | Provider 详情 |
| PUT | `/models/providers/{provider_id}` | 是 | 更新 provider |
| DELETE | `/models/providers/{provider_id}` | 是 | 删除 provider |
| POST | `/models/providers/{provider_id}/actions/set-default` | 是 | 设为默认 provider |
| POST | `/models/providers/{provider_id}/actions/test-connection` | 是 | 测试 provider 连接 |
| GET | `/models/providers/{provider_id}/remote-models` | 否 | 拉取远端模型列表 |
| POST | `/models/providers/{provider_id}/models` | 是 | 新增 provider model |
| PUT | `/models/providers/{provider_id}/models/{model_id}` | 是 | 更新 provider model |
| DELETE | `/models/providers/{provider_id}/models/{model_id}` | 是 | 删除 provider model |
| GET | `/models/presets` | 否 | Model preset 绑定 |
| PUT | `/models/presets/{preset_key}` | 是 | 更新 preset 绑定 |
| GET | `/models/invocations` | 否 | Model invocation 记录 |

### Dashboard / Events

| 方法 | 路径 | Capability | 说明 |
| --- | --- | --- | --- |
| GET | `/dashboard/summary` | `runtime.inspect` | Dashboard 首屏聚合摘要 |
| GET | `/events` | `runtime.inspect` | 标准事件列表、筛选回显、summary buckets 和分页 |
| GET | `/events/{event_id}` | `runtime.inspect` | 标准事件详情摘要和状态流转 |

### Runtime / Inspect

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/runtime/health` | runtime 健康摘要 |
| GET | `/runtime/audit/news` | runtime audit news 列表 |
| GET | `/runtime/errors` | runtime error 列表 |
| GET | `/runtime/errors/{error_id}` | runtime error 详情 |
| GET | `/agents/runs` | Agent run 列表 |
| GET | `/agents/runs/{run_id}` | Agent run 详情 |
| GET | `/tools/invocations` | Tool invocation 列表 |
| GET | `/tools/invocations/{invocation_id}` | Tool invocation 详情 |
| GET | `/scheduler-runs` | Scheduler run 列表 |
| GET | `/scheduler-runs/{run_id}` | Scheduler run 详情 |
| GET | `/raw-events` | Raw event 列表 |
| GET | `/raw-events/{raw_event_id}` | Raw event 详情 |

### Wallet

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/wallet/accounts/{account_id}` | paper wallet 账户概览 |
| GET | `/wallet/accounts/{account_id}/cash-balances` | 现金余额 |
| GET | `/wallet/accounts/{account_id}/positions` | 持仓 |
| GET | `/wallet/accounts/{account_id}/ledger-entries` | 流水 |
| GET | `/wallet/accounts/{account_id}/paper-orders` | 模拟订单 |
| GET | `/wallet/accounts/{account_id}/paper-executions` | 模拟成交 |

### Debug

以下路由仅在非 production 环境注册：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/debug/success` | 调试成功 envelope |
| GET | `/debug/error` | 调试错误 envelope |
| POST | `/debug/validation` | 调试请求体验证 |

## 维护方式

- 新增或删除 API route 时，同步更新本文档和对应模块文档。
- 行为、权限、CSRF、payload 或 envelope 变化时，应优先以 OpenSpec / design / schema 为真源，再更新本目录。
- 本目录不替代 `/openapi.json`；字段级 schema 仍以运行时 OpenAPI 和 API schema 代码为准。
