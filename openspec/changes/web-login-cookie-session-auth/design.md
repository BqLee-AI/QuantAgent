## Context

issue #97 要为 `apps/web` 接入后端已经稳定的 Cookie Session auth 契约。当前前端只有管理台路由壳、占位页面和共享 API client；`createApiClient` 仍保留 Bearer token 注入与 401 refresh 语义，`router` context 只有 capability placeholder，`MainLayout` 默认对所有路由渲染完整后台壳，没有登录入口和统一未登录态。

后端 stable spec 已经固定以下约束：

- `POST /api/v1/auth/login` 成功后返回 `actor_id`、`actor_type`、`capabilities`、`csrf_token`，并由浏览器托管 HttpOnly session cookie。
- `GET /api/v1/me` 是前端启动/刷新时恢复登录态的唯一 bootstrap 入口。
- `POST /api/v1/auth/logout` 需要有效 `X-CSRF-Token`，成功后清理 session cookie。
- 401 与 403 使用标准 envelope，且不得泄露敏感值。
- development `AUTH_ENABLED=false` 时，后端 `/login` 与 `/me` 返回 development bypass actor。

本 change 需要把这些约束转成前端统一行为，但仍保持范围克制：只处理前端登录入口、Cookie Session bootstrap、受保护路由、logout、CSRF 注入、401/403 收口和 development bypass，不新增多用户、RBAC、OAuth、SSO，也不把登录变成通用多产品 auth 框架。

## Goals / Non-Goals

**Goals:**

- 定义独立 `/login` 路由与受保护管理台路由的边界。
- 定义前端 auth bootstrap 状态模型及其非敏感字段边界。
- 定义应用启动、刷新、未登录、session 失效、logout 和 development bypass 的统一处理路径。
- 收敛 `apps/web/src/shared/api/` 的鉴权行为，使其适配 Cookie Session + CSRF，而不是继续扩展 Bearer refresh 语义。
- 收敛 `apps/web/src/shared/config/` 的 runtime auth 开关读取，避免组件自行解释 `authEnabled`。
- 为后续页面接入提供统一入口，避免页面组件手写 auth 请求、`X-CSRF-Token` 和 401 跳转逻辑。

**Non-Goals:**

- 不实现用户注册、改密码、找回密码、多用户、多租户、RBAC、OAuth、SSO 或生产账号管理。
- 不在前端保存或暴露 session cookie、password、password hash、signing secret、真实 token 或私有策略。
- 不把 capability 隐藏导航当作真实权限边界。
- 不在本轮实现完整业务页面的数据接入、审批处理、插件配置或执行能力。
- 不把 Bearer token 或 refresh token replay 作为本轮主鉴权路径。

## Decisions

### 1. 登录入口使用独立 `/login` 路由

登录页与后台壳分离，避免在 `MainLayout` 内同时承载未登录态和管理台导航。受保护业务路由在无 session 时统一跳转 `/login`，登录成功后恢复原目标路由；直接访问 `/login` 时登录成功回默认首页流。

替代方案是在现有后台壳内渲染登录面板。该方案会把未登录态与后台导航、面包屑混在一起，增加路由守卫和布局判断复杂度，因此不采用。

### 2. 前端 auth 状态只保存非敏感 bootstrap 数据

前端仅维护 `actor_id`、`actor_type`、`capabilities`、`csrf_token` 以及 bootstrapping/authenticated/unauthorized 等状态位。HttpOnly cookie 只由浏览器托管，password 只作为登录表单瞬时输入值，不进入持久存储或共享状态。

替代方案是把 cookie/token/refresh 数据也放入前端状态。该方案违背后端 Cookie Session 契约和 issue 非目标，因此不采用。

### 3. 应用启动统一通过 `/me` bootstrap

应用启动、硬刷新和从 development bypass 进入管理台时，统一通过 `GET /api/v1/me` 恢复当前 actor、capabilities 和 `csrf_token`。前端不自行推断登录态，不通过 localStorage 恢复 auth，不在页面组件单独发 bootstrap 请求。

替代方案是登录成功后把 actor 或 token 永久缓存到本地存储，刷新时直接复用。该方案会引入过期状态和敏感信息存储风险，因此不采用。

### 4. `AUTH_ENABLED=false` 走 development bypass，而不是继续展示登录页

当 runtime config 的 `authEnabled` 为 `false` 时，前端仍执行 bootstrap，但不要求用户停留在 `/login`；只有当 `/me` 返回 development actor 时才直接进入管理台，并在 UI 中保留清晰的 development/auth-disabled 状态提示。该路径不是生产默认行为。

替代方案是开发态也强制展示登录页。该方案会让本地开发与后端 development bypass 语义不一致，也会削弱开发环境下的效率，因此不采用。

### 5. `src/shared/api/` 收口到 Cookie Session + CSRF 语义

现有 `createApiClient` 已经固定 `withCredentials=true`，这是可复用的。但 `Authorization` 注入和 `refreshAccessToken` 语义与本轮目标不一致，因此应把鉴权入口收敛为：

- 浏览器自动带 HttpOnly cookie；
- 前端从 auth bootstrap 状态统一注入 `X-CSRF-Token` 到 logout 和受保护写请求；
- 401 统一触发 unauthorized 收口与状态清理；
- 403 维持权限不足语义，不伪装成网络错误。

如果出于兼容原因暂时保留 Bearer 或 refresh 扩展点，也必须明确它们不是本轮登录接入主路径，不得要求登录页、`/me` bootstrap、logout 或受保护写请求依赖本地存储 token 或 refresh replay 才能成立。

替代方案是保留 Bearer 和 refresh 逻辑，同时再叠加 Cookie Session。该方案会让 auth 行为双轨化，后续页面不清楚哪条路径才是主路径，因此不采用。

### 6. 前端边界按 `app` / `routes` / `shared` 收口

本轮 auth 能力必须贴合现有前端边界：

- 路由页面放在 `apps/web/src/routes/`；
- provider、router、layout 放在 `apps/web/src/app/`；
- API 调用与 header 注入收敛在 `apps/web/src/shared/api/`；
- runtime config 读取收敛在 `apps/web/src/shared/config/`。

替代方案是让页面组件直接调用接口、手写 `X-CSRF-Token` 或各自处理 401 跳转。该方案会让鉴权逻辑分叉，后续页面难以复用，因此不采用。

### 7. capability 初版只展示状态，不裁剪主导航

后端 capability guard 已经是权限真源，前端当前页面也仍是占位态。初版只在统一 auth 状态或顶层 UI 中展示 actor/capabilities 信息，不对现有主导航做强制隐藏，以避免过早固化 capability-to-nav 映射。

替代方案是先隐藏部分高风险入口或全面按 capability 裁剪。该方案需要本轮同时定义完整前端映射表，而当前页面多数仍未落地真实能力，因此不采用。

## Risks / Trade-offs

- [Risk] 现有 API client 的 Bearer / refresh 测试与实现语义会和新 spec 冲突。  
  -> Mitigation: 在 spec 和 tasks 中明确它们属于待收口边界，实现时优先修改 `apps/web/src/shared/api/`，而不是在页面层绕过。

- [Risk] 登录页和后台壳拆分后，路由跳转逻辑可能出现重复跳转或回环。  
  -> Mitigation: 明确 `/login` 为公共路由，受保护路由统一 guard，并把“原目标地址恢复”作为 requirement 与测试场景。

- [Risk] development bypass 与生产鉴权路径行为不同，容易让实现者误把 bypass 当默认路径。  
  -> Mitigation: 明确 bypass 只在 `AUTH_ENABLED=false` 生效，并要求 UI 有显式开发态标记。

- [Risk] capability 先只展示状态，短期内无法在 UI 上隐藏高风险入口。  
  -> Mitigation: 在 spec 中强调后端 guard 才是权限真源，前端导航裁剪留待后续 change。
