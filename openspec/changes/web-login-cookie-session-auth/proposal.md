## Why

后端 `apps/api` 已经落地本地单用户 Cookie Session 鉴权闭环，并通过稳定 spec 固定了 `POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/me`、HttpOnly session cookie、`csrf_token` 与 401/403 envelope。前端如果继续停留在路由壳和占位页面阶段，后续受保护页面会各自处理登录态、401、CSRF、capability 和跳转，导致 auth bootstrap 与 API 行为分叉。

issue #97 先只收住前端最小登录入口与 Cookie Session bootstrap 边界，为后续管理台页面提供统一的登录、会话恢复、logout 和未授权处理入口，不在本 change 中扩展成完整账号系统。

## What Changes

- 为 `apps/web` 定义最小前端登录接入主路径：`POST /api/v1/auth/login`、`GET /api/v1/me`、`POST /api/v1/auth/logout`。
- 定义独立 `/login` 公共路由、受保护管理台路由统一 guard、未登录跳转和登录后恢复原目标地址。
- 定义前端 auth bootstrap 状态边界，只保存 `actor_id`、`actor_type`、`capabilities`、`csrf_token` 与必要状态位；HttpOnly session cookie 由浏览器托管。
- 收敛 `apps/web/src/shared/api/` 与 `apps/web/src/shared/config/` 的职责：统一处理 Cookie Session、`X-CSRF-Token`、401/403 收口与 development bypass 入口，不在页面组件散落裸请求和手写 header。
- 明确本轮只做前端登录入口、Cookie Session bootstrap、受保护路由、logout、CSRF 注入、401/403 收口和 development bypass。
- 明确本轮不做注册、找回密码、多用户、RBAC、OAuth、SSO、生产账号管理、真实权限系统或业务页面数据接入。

## Capabilities

### New Capabilities
- `web-login-cookie-session-auth`: 定义前端登录页、auth bootstrap、受保护路由、logout、CSRF token 注入和 development bypass 的统一行为。

### Modified Capabilities
- `router-layout`: 路由与布局 requirement 从“所有页面始终在统一后台壳内”扩展为“登录页与受保护管理台路由分离，并支持统一未登录跳转与登录后恢复目标地址”。
- `api-client-error-governance`: API client requirement 从 Bearer token / 401 refresh 默认路径收敛为 Cookie Session + `X-CSRF-Token` + 统一 unauthorized 收口，并明确 Bearer/refresh 不是本轮主鉴权路径。

## Impact

- `apps/web/src/routes/**`：新增 `/login` 路由，并让受保护管理台页面通过统一 guard 进入。
- `apps/web/src/app/**`：承接 auth bootstrap、provider、router context、layout 分层与登录态展示。
- `apps/web/src/shared/api/**`：统一处理 Cookie Session、`X-CSRF-Token`、401/403 和 logout。
- `apps/web/src/shared/config/**`：统一承接 `authEnabled` 与 development bypass 判断。
- `apps/web` 测试层：补充 login、`/me` bootstrap、protected route、logout、401/403 与 auth-disabled 场景。
- `openspec/specs/router-layout/spec.md` 与 `openspec/specs/api-client-error-governance/spec.md`：补充与 stable backend auth spec 对齐的前端行为 delta。
