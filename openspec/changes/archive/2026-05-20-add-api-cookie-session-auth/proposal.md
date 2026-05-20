# Change: 落地 apps/api 单用户 Cookie Session 鉴权闭环

## 来源

- GitHub issue: https://github.com/BqLee-AI/QuantAgent/issues/86
- 上游决策 issue: https://github.com/BqLee-AI/QuantAgent/issues/79
- Issue 标题：`[DEV] 落地 apps/api 单用户 Cookie Session 鉴权闭环`
- Labels: `type:feature`, `area:api`, `area:risk`, `area:openspec`, `priority:high`, `complexity:large`, `status:ready`
- 状态：OPEN

## Issue 归一化

本 change 只关闭一个问题：为 `apps/api` 初版本地单用户 HTTP cookie/session 鉴权建立可审核、可实现的 OpenSpec 边界，并在审核通过后支持最小 API 鉴权闭环实现。

它现在重要，是因为 #79 已经确认初版采用本地单用户 cookie/session + capability，不做完整用户系统、RBAC、多租户、OAuth 或 SSO。如果后续插件配置、secret 管理、approval、executor dry-run、runtime inspect 等敏感接口先裸奔实现，各 router 会各自发明 session、actor、capability、CSRF 和 audit 字段，导致安全边界和审计链路分叉。

影响区域：`apps/api` HTTP 边界、API 错误 envelope、auth route 契约、OpenAPI 契约测试、后续高风险 API 的 actor/audit context 传递口径。

## 当前基线

- `apps/api` 已有 FastAPI app factory、统一 `code/data/msg/error` 响应 envelope、全局异常处理、`X-Request-ID` middleware、数据库 lifespan、请求级 DB session dependency、`/api/v1/health`、`/api/v1/ready`、`/api/v1/version` 和 OpenAPI 契约测试骨架。
- `GET /api/v1/health` 是 public liveness probe，不依赖数据库或业务表。
- `GET /api/v1/ready` 是数据库 readiness probe，只验证配置的数据库可达。
- `GET /api/v1/version` 是非业务示例 route，只展示 DTO、provider、envelope 和 OpenAPI 契约。
- 现有错误体系已有 `AppError` 和统一异常处理，但还没有 `UnauthorizedError` / `ForbiddenError`。
- 当前没有 API auth dependency、session cookie、CurrentActor、capability guard、CSRF guard 或 actor/audit context helper。

相关真源：

- `docs/design/08-api-and-websocket-design.md`：HTTP API 使用统一 envelope；HTTP status 仍保留；未授权为 401；敏感配置、secret、私有策略和 prompt 不得通过 API 明文泄露；高风险动作必须经过 Policy Gate。
- `docs/design/09-frontend-architecture-design.md`：前端基于 `/me` 类接口获取 capabilities；前端隐藏入口只作为 UX，后端必须做真实权限校验。
- `docs/prd/06-risk-constraints.md`：API keys、交易账户信息、策略参数、私有关键词、行业规则、自动执行权限配置属于敏感信息；日志和 API 响应不得输出完整密钥或私有策略。

## 目标

- 定义并实现本地单用户 cookie/session 鉴权的 API 边界。
- 增加 auth settings，并固定生产安全默认值，避免 production 弱默认；当前 local Docker compose 不等同 production，生产部署必须显式使用 production 配置。
- 支持管理员口令登录并签发 HttpOnly session cookie。
- 支持 logout 清除 session cookie。
- 暴露 `/api/v1/me`，返回当前 actor 和 capability 快照。
- 定义 CurrentActor、固定 capability 集合和 capability guard。
- 统一 401/403 错误为 `AppError` 体系内的 envelope，并携带 `request_id`。
- 固定 public/protected route 默认规则：系统探针 public，业务 API 默认 protected。
- 为 cookie session 写操作定义 CSRF 基础契约，默认 header 为 `X-CSRF-Token`。
- 固定 actor/audit context helper 的传递口径，供后续高风险 API 复用。

## 非目标

- 不实现用户注册、改密码、密码找回、邮箱验证、OAuth 或 SSO。
- 不实现多用户、多组织、多租户数据隔离。
- 不实现完整 RBAC，例如 admin/editor/viewer 角色体系。
- 不创建用户表、session 表、完整 `audit_logs` 表或相关 migration。
- 不实现插件配置、secret 管理、approval、executor dry-run、runtime inspect 的业务接口。
- 不实现前端登录页面、前端 auth store 或 Web E2E。
- 不提交真实 secret、cookie、session、管理员口令、私有策略、交易密钥或真实 `.env`。
- 不把 capability 伪装成完整用户权限系统。
- 不引入真实交易执行、真实生产凭证或 live trading 能力。

## 已定决策

- 初版鉴权采用 HTTP cookie/session，不使用 Bearer token 作为主方案。
- 初版只有本地 actor，例如 `local_admin`；development 关闭鉴权时使用 `local_dev` 或等价 actor，避免审计字段为空。
- session 来源为极简 `POST /api/v1/auth/login`，用本地配置管理员口令换取 HttpOnly session cookie。
- cookie 始终 `HttpOnly`；development 和当前 local Docker compose 可允许 `Secure=false`；production 必须 `Secure=true`；默认 `SameSite=Lax`。
- public route 白名单为 `GET /api/v1/health`、`GET /api/v1/ready`、`GET /api/v1/version`；其它业务 API 默认 protected。
- capability 固定集合集中维护，至少包含 `runtime.inspect`、`plugin.configure`、`plugin.install`、`secret.manage`、`approval.approve`、`approval.amend`、`executor.dry_run`。
- 后端必须校验 capability；前端隐藏按钮不能作为权限边界。
- cookie session 写操作首轮即要求 CSRF token；login 成功响应和 `/api/v1/me` 返回非敏感 `csrf_token` 快照，写操作默认通过 `X-CSRF-Token` header 提交。
- `AUTH_ENABLED=false` 仅允许 development；production 下关闭鉴权必须启动失败或被强制拒绝。
- 401/403 扩展现有 `AppError`，继续输出统一 envelope 和 `request_id`。

## 变更内容

- 新增 API auth settings、cookie/session 配置、安全默认值和 development-only auth disabled 规则。
- 新增 session 签发、校验、过期和清除的 API 层能力，保持不落数据库表。
- 新增 CurrentActor、固定 capability 集合、capability guard 和 actor/audit context helper。
- 新增 `/api/v1/auth/login`、`/api/v1/auth/logout`、`/api/v1/me` route 契约。
- 新增 CSRF token 获取和写操作校验基础：login 成功响应和 `/api/v1/me` 提供 `csrf_token`，logout 与 protected write routes 使用 `X-CSRF-Token` 校验。
- 新增 `UnauthorizedError` / `ForbiddenError` 或等价 `AppError` 扩展。
- 增加 route runtime tests、OpenAPI schema tests、auth enabled/disabled tests、CSRF tests、sensitive information non-disclosure tests。
- 更新 `apps/api/README.md` 记录 auth 相关环境变量、public/protected 规则、最小验证命令和非目标。

## 验收标准

- OpenSpec-only PR 审核通过后才进入实现 PR；在审核通过前不修改 API runtime 代码、不新增依赖、不提交实现。
- public routes 可匿名访问：`GET /api/v1/health`、`GET /api/v1/ready`、`GET /api/v1/version`。
- protected route 缺 session 返回 HTTP 401，`error.code=UNAUTHORIZED`。
- capability 不足返回 HTTP 403，`error.code=FORBIDDEN`。
- 正确管理员口令可通过 `/api/v1/auth/login` 换取 HttpOnly session cookie。
- `/api/v1/auth/logout` 可清除 session cookie。
- `/api/v1/me` 返回当前 actor 和 capability 快照，不暴露 session、cookie、签名、secret 或口令。
- login 成功响应和 `/api/v1/me` 提供非敏感 `csrf_token`；logout、测试中的 protected write route（`/test/protected-write`）缺少或携带无效 CSRF token 时被拒绝，携带有效 token 时通过。
- actor/audit context helper 可以把 current actor 和 request metadata 安全传递给后续 handler。
- API 响应、日志和测试输出不包含管理员口令、hash、session、cookie、签名 secret、私有策略或 stack trace。
- OpenAPI 中 auth routes 使用 `ApiResponse[T]` envelope、显式 tags 和稳定 schema。

## 失败信号

- 没有 OpenSpec-only PR 审核就直接实现代码。
- 401/403 绕开统一 envelope，或缺少 `request_id`。
- 业务 API 默认匿名可访问。
- router 直接手写 cookie 解析、capability 字符串判断或 CSRF 校验。
- `/me` 返回 session 原文、cookie 值、签名 secret、管理员口令或 hash。
- production 默认 `Secure=false`，允许无保护关闭鉴权，或把当前 local Docker compose 误写成 production 安全默认。
- CSRF header/token 获取口径不稳定，或实现者在 login、`/me`、单独 endpoint 之间自行选择，导致前端无法统一接入。
- actor/audit context 中包含 session、cookie、签名、口令或 secret 原文。
- 把本 change 扩大为完整用户系统、RBAC、多租户、业务审批或插件配置实现。

## 依赖与顺序

- 无外部服务依赖。
- 必须先提交并审核本 OpenSpec change。
- 审核通过后，先实现 settings 和安全默认值，再实现 session/actor/capability/CSRF，最后接入 routes、tests 和 README。
- 本 change 不要求真实 PostgreSQL、Docker、Web E2E、真实 secret、真实交易或外部服务。

## 待确认问题

当前无阻塞问题。实现细节按 #79 和 #86 中已确认推荐方案执行。

## 人工审核门禁

本 proposal、`design.md`、`tasks.md` 和 spec delta 是 implementation 前的 review target。新建或大幅更新本 change 后，必须先创建 OpenSpec-only PR 并等待维护者明确评论“没问题”或批准。维护者认可前，不允许实现代码、添加依赖、修改 API runtime 或把 spec artifacts 与 implementation 混在同一个 PR 中。

## 验证

- `openspec validate add-api-cookie-session-auth --type change --strict --json`
- 实现阶段再运行：`cd apps/api && uv run python -m unittest discover -s src/tests`
