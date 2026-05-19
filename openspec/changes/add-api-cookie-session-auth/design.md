# Design: apps/api 单用户 Cookie Session 鉴权闭环

## 背景

`apps/api` 当前已经完成 API v1 路由与契约骨架：统一 `code/data/msg/error` envelope、`X-Request-ID`、全局异常处理、数据库 readiness、`/api/v1/health`、`/api/v1/ready`、`/api/v1/version`、标准 router 注册 helper、route runtime tests 和 OpenAPI 契约测试。

缺口是所有后续敏感 API 都缺少统一的 auth 前提。#79 已经确认初版采用本地单用户 cookie/session + capability，不做完整用户系统、RBAC、多租户、OAuth 或 SSO。#86 将此前拆散的 login/logout、`/me`、CSRF、actor/audit context 等 issue 合并为一个最小闭环。

本设计只定义并实现 API 鉴权基础设施和最小 auth route。它不实现插件配置、secret 管理、approval、executor dry-run 或 runtime inspect 业务接口。

## 目标

- 在 `apps/api` 内形成浏览器可用的本地单用户 cookie session 登录态。
- 让后续业务 API 能复用统一 CurrentActor、capability guard 和 CSRF guard。
- 固定 public/protected route 默认规则，避免新增业务 route 默认匿名。
- 让前端可通过 `/api/v1/me` 获取当前 actor 和 capabilities。
- 保持 API 响应 envelope、request id、OpenAPI 契约和敏感信息脱敏规则一致。

## 非目标

- 不创建数据库用户/session/audit 表。
- 不实现完整用户生命周期、RBAC、多租户、OAuth、SSO 或生产账号安全策略。
- 不实现前端页面、generated client、static OpenAPI artifact 或 Web E2E。
- 不实现高风险业务 API 本身。
- 不替代后续 Policy Gate、approval、secret 管理、executor dry-run 或 audit persistence。

## 规范分层与决策状态

### 规范分层

- `specs/api-cookie-session-auth/spec.md` 定义外部行为和可验收场景。
- `proposal.md` 定义 issue 来源、范围、非目标和验收意图。
- `design.md` 固定本阶段架构边界、安全取舍和失败路径。
- `tasks.md` 定义审核门禁、依赖图、写入边界和验证动作。

以下内容是实现细节或派生视图，不是本 change 的契约真源：

- FastAPI 自动生成的 OpenAPI component 名称。
- 测试中使用的内部 helper 名称。
- cookie/session 签名算法的具体库，只要满足本设计的安全边界。

### 本阶段已定

- 使用 HTTP cookie/session。
- 使用本地配置管理员口令登录。
- 使用 HttpOnly session cookie。
- 使用固定 capability 集合。
- 使用 `X-CSRF-Token` 作为默认 CSRF header。
- 使用 `AppError` 体系表达 401/403。
- OpenSpec-only PR 审核通过前不进入实现。

### 后续可演进但本阶段不做

- 多用户、多角色、多租户。
- 数据库存储用户、session 或 audit log。
- OAuth、SSO、一次性授权链接。
- 静态 OpenAPI artifact 和 generated TypeScript client。
- 更完整的 password policy、lockout、rotation 或 admin password management。

## 关键决策

### 鉴权入口采用 login/logout/me 三个 route

`POST /api/v1/auth/login` 用本地配置管理员口令换取 session cookie。登录成功只通过 Set-Cookie 写入 session，不在响应体返回 session 原文。

`POST /api/v1/auth/logout` 清除 session cookie。logout 属于 cookie-session 写操作，必须要求有效 `X-CSRF-Token`；缺失或无效 token 返回统一错误 envelope，成功后清除 session cookie，响应体不得包含 session、cookie 或 token 原文。

`GET /api/v1/me` 返回当前 actor 和 capability 快照。它不返回 session id、cookie、签名、口令、hash、secret 或部署内部敏感配置。

影响：前端可以形成稳定登录态处理，但本 change 不实现前端页面。

### Cookie 安全属性按环境收紧

session cookie 始终 `HttpOnly`，默认 `SameSite=Lax`。

development 允许 `Secure=false`，便于本地 HTTP 和 FastAPI TestClient 验证。当前仓库 local Docker compose 默认 `APP_ENV=local`，不等同 production；如果 Docker 用于 production deployment，必须显式设置 production environment 并使用 `Secure=true`。

如果 production 配置会导致弱默认，例如关闭鉴权或允许 insecure cookie，应在应用启动或 settings validation 时失败，不能静默降级。

影响：本地开发可用，生产默认安全。

### Auth disabled 仅允许 development

`AUTH_ENABLED=false` 只允许 `APP_ENV=development`。disabled 模式不是匿名模式；它必须生成稳定 actor，例如 `local_dev`，并携带 capability 快照，让后续 handler 的 actor/audit 字段不为空。

production 下如果 `AUTH_ENABLED=false`，应用应启动失败或拒绝该配置。

影响：开发调试便利性不破坏生产安全边界。

### Public route 使用白名单，业务 API 默认 protected

public route 固定为：

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/version`

development debug routes 只用于非生产诊断，不作为业务 API public 规则的扩展。

后续业务 API 默认 protected。新增 public route 必须显式说明理由，并在 OpenAPI/tests 中可见。

影响：只读业务 API 也不会因为是 GET 而默认匿名暴露。

### Capability 固定集合集中维护

初版 capability 不从数据库或配置动态读取，而是在代码中集中维护固定集合。至少包含：

- `runtime.inspect`
- `plugin.configure`
- `plugin.install`
- `secret.manage`
- `approval.approve`
- `approval.amend`
- `executor.dry_run`

local admin 默认拥有全部 capability。后续是否允许配置裁剪 capability 需要独立 change。

route 不能散落手写 capability 字符串判断，应通过统一 guard 或 dependency 校验。

影响：避免 RBAC 过早复杂化，同时防止 capability 命名漂移。

### CSRF 首轮进入 cookie session 闭环

使用 cookie session 后，写操作需要 CSRF 防护。默认 header 为 `X-CSRF-Token`。

CSRF token 获取口径固定为 login 成功响应和 `/api/v1/me` response 都返回非敏感 `csrf_token` 快照。本 change 不新增单独 CSRF/bootstrap endpoint，避免扩大初版 route surface。

login 可豁免 CSRF，因为登录前通常没有 session；本 change 只有 login 可豁免 CSRF，logout 和 protected write route 必须要求有效 `X-CSRF-Token`。`csrf_token` 不是 session、cookie、签名 secret 或 raw token material，不得在响应中暴露可伪造 session 的秘密。

影响：后续插件配置、secret、approval、executor dry-run 等敏感写操作可直接复用同一防线。

### 401/403 进入 AppError envelope

未登录、session 缺失、session 无效或过期返回 HTTP 401，`error.code=UNAUTHORIZED`。

已登录但 capability 不足返回 HTTP 403，`error.code=FORBIDDEN`。

错误响应继续使用 `code/data/msg/error` envelope，并携带与响应头一致的 `request_id`。

错误响应不得泄露 cookie、session、签名、口令、secret、连接串或 stack trace。

影响：前端 client、代理和测试都可以依赖 HTTP status 与统一 envelope。

### Actor/audit context 只传递脱敏身份与请求元数据

本 change 不落完整 audit persistence，但需要提供后续高风险 API 可复用的 context 口径。

context 至少表达：

- actor id
- actor type
- capabilities 或当前校验 capability
- request id
- request method/path 或等价 request metadata

context 不得包含 session 原文、cookie 值、签名 secret、管理员口令、hash 或私有策略。

影响：后续 audit log 和 Policy Gate 能复用同一 actor 语义。

## 契约边界

### API route 边界

本 change 新增 auth routes，均挂载在 `/api/v1` 下：

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/me`

routes 必须显式声明 FastAPI `response_model=ApiResponse[T]` 和 OpenAPI tags。

### DTO 边界

request/response DTO 放在 `apps/api/src/quantagent/api/schemas/`。DTO 不能直接复用 ORM model，也不能返回临时 dictionary 作为长期契约。

`/me` response DTO 必须是脱敏 actor/capability snapshot。

### Provider 与 service 边界

当前 `apps/api/src/quantagent/api/providers/` 只用于 sample data 或轻量替换点。auth 可使用 API 私有 helper，但不能把可复用领域能力长期沉淀在 router 里。

如果后续需要 worker、scheduler、插件或其他 package 复用 auth/session 基础能力，应另行判断是否下沉到 `packages/core`。

### Persistence 边界

本 change 不新增数据库表、migration、repository 或 request-level commit 行为。session 可以是签名 cookie 或等价无数据库方案。请求级 DB session dependency 不应被 auth dependency 隐式 commit。

### Frontend 与 contracts 边界

本 change 不提交 static OpenAPI artifact、generated client、TypeScript types 或 Zod schema。OpenAPI 验证仍基于 FastAPI runtime `/openapi.json`。

### Debug route 边界

debug route 只用于非生产诊断。新增 auth debug 或测试辅助 route 必须在 production app 和 production OpenAPI 中不可见。

## 数据流与控制流

登录成功路径：

```text
client
  -> POST /api/v1/auth/login
  -> validate local admin credential
  -> create signed session and csrf_token snapshot
  -> Set-Cookie HttpOnly session
  -> ApiResponse.success(login snapshot with csrf_token, without session secret)
```

受保护读取路径：

```text
client
  -> protected route
  -> request id middleware
  -> auth dependency validates session
  -> CurrentActor attached or passed to handler
  -> optional capability guard
  -> route returns ApiResponse[T]
```

受保护写路径：

```text
client
  -> protected write route
  -> auth dependency validates session
  -> CSRF guard validates X-CSRF-Token
  -> optional capability guard
  -> route returns ApiResponse[T]
```

auth disabled development 路径：

```text
APP_ENV=development + AUTH_ENABLED=false
  -> auth dependency returns local_dev actor
  -> capability snapshot remains non-empty
  -> audit context remains populated
```

## 失败路径

- 缺少 session：401 `UNAUTHORIZED` envelope。
- session 无效或过期：401 `UNAUTHORIZED` envelope。
- capability 不足：403 `FORBIDDEN` envelope。
- CSRF token 缺失或无效：403 或 auth-specific forbidden envelope，错误码必须稳定且不泄露 submitted token、expected token 或 token derivation material。
- production 下关闭鉴权：应用启动失败或 settings validation 失败。
- production 下 insecure cookie 默认：应用启动失败或 settings validation 失败；当前 local Docker compose 不能被文档或实现误判为 production 安全默认。
- 管理员口令错误：401 envelope，不说明口令是否存在或如何匹配。
- 未配置管理员口令或 session secret：非 development 环境启动失败；development 可有明确降级或测试默认，但不得误用于 production。

禁止的失败处理方式：

- 在 route 中直接抛裸 `HTTPException` 导致 envelope 不一致。
- 在响应体返回 session/cookie/signature/password/hash。
- 在日志或测试失败输出中打印完整 secret。
- 为了通过测试把业务 route 临时加入 public 白名单。

## 可观测性与安全

- 所有 auth 错误响应头与错误体中的 `request_id` 必须一致。
- 登录失败、CSRF 失败、capability 失败可记录脱敏日志，但不得记录完整 secret、cookie、session、口令、hash 或私有策略。
- actor/audit context 应包含 request metadata，便于后续审计链路落地。
- 本 change 不新增生产 metrics、trace pipeline 或 audit persistence。

## 备选方案

### Bearer token

放弃。#79 已确认初版使用 cookie/session；Bearer token 不作为初版主方案。

### 只依赖 SameSite=Lax，延后 CSRF

放弃。后续敏感写操作会依赖 cookie session，延后 CSRF 会迫使前端 client、测试和 route dependency 返工。

### 预创建用户/session/audit 表

放弃。当前阶段明确不做完整用户系统、多用户、多租户或 audit persistence。

### 每个业务 router 自行判断 auth/capability

放弃。会导致 capability 命名、错误 envelope、CSRF 和 actor/audit context 分叉。

## 人工审核门禁

本 design 属于 implementation 前的 review target。OpenSpec-only PR 获得维护者明确认可前，不允许实现代码、添加依赖、修改 API runtime 或把本 change 与实现混在同一个 PR 中。
