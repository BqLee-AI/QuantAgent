## ADDED Requirements

### Requirement: Dedicated Login Route

`apps/web` SHALL 提供独立的 `/login` 路由作为本地单用户管理台的登录入口，而不是在后台壳内混合渲染未登录面板。

#### Scenario: Login route renders outside the dashboard shell

- **WHEN** 用户直接访问 `/login`
- **THEN** 页面渲染登录界面
- **AND** 不渲染受保护管理台的侧边栏、面包屑或业务主体内容

### Requirement: Protected Route Guard

受保护的管理台路由 SHALL 通过统一 guard 处理未登录访问，而不是由页面组件各自判断 session 或 401。

#### Scenario: Anonymous access redirects to login

- **WHEN** 未登录用户访问受保护管理台路由
- **THEN** 前端跳转到 `/login`
- **AND** 不渲染需要 auth 的业务 UI
- **AND** 不在页面组件里散落裸 `fetch` 或重复 401 判断

#### Scenario: Login success restores the original target

- **WHEN** 用户原本访问受保护目标路由并被跳转到 `/login`
- **AND** 用户成功登录
- **THEN** 前端回到原目标路由

#### Scenario: Direct login falls back to default entry flow

- **WHEN** 用户直接访问 `/login`
- **AND** 用户成功登录
- **THEN** 前端进入默认首页流

### Requirement: Login Bootstrap State

前端 SHALL 维护统一的 auth bootstrap 状态，并且只保存非敏感字段。

#### Scenario: Login success stores only non-sensitive fields

- **WHEN** `POST /api/v1/auth/login` 成功
- **THEN** 前端状态只保存 `actor_id`、`actor_type`、`capabilities`、`csrf_token` 和必要的登录状态字段
- **AND** 不保存 session cookie、cookie value、password、password hash、signing secret 或真实 token 原文

#### Scenario: Sensitive values are not persisted

- **WHEN** 开发者检查前端 auth bootstrap 的状态与持久化路径
- **THEN** localStorage、sessionStorage、React state、共享状态和日志中都不包含 password、password hash、session、cookie value、signing secret、真实 token 或私有策略原文

### Requirement: Session Bootstrap Via Me

应用启动、刷新和会话恢复 SHALL 统一通过 `GET /api/v1/me` 完成。

#### Scenario: Refresh restores authenticated actor

- **WHEN** 浏览器已经持有有效 session cookie
- **AND** 用户刷新页面或重新打开前端
- **THEN** 前端通过 `GET /api/v1/me` 恢复 `actor_id`、`actor_type`、`capabilities` 和 `csrf_token`

#### Scenario: Missing session enters unauthorized state

- **WHEN** 前端 bootstrap 调用 `GET /api/v1/me`
- **AND** 后端返回 401
- **THEN** 前端进入统一未登录态
- **AND** 受保护管理台路由跳转到 `/login`

### Requirement: Development Auth Disabled Bypass

当 runtime config 的 `authEnabled` 为 `false` 时，前端 SHALL 与后端 development bypass 语义保持一致。

#### Scenario: Auth-disabled development bypass enters the dashboard

- **WHEN** 前端运行于 development 配置
- **AND** `authEnabled` 为 `false`
- **AND** `/me` 返回 development actor
- **THEN** 前端不强制停留在 `/login`
- **AND** 直接进入管理台
- **AND** UI 中存在明显的 development 或 auth-disabled 状态提示

#### Scenario: Bypass is not treated as the production default

- **WHEN** `authEnabled` 不为 `false`
- **OR** `/me` 未返回 development actor
- **THEN** 前端不得把 development bypass 当作默认登录路径
- **AND** 仍按正常登录或未登录流程处理

### Requirement: Logout Uses CSRF Token

前端 SHALL 通过统一 logout action 调用 `POST /api/v1/auth/logout`，并携带当前 `X-CSRF-Token`。

#### Scenario: Logout clears front-end bootstrap state

- **WHEN** 已登录用户触发 logout
- **AND** 前端使用当前 `csrf_token` 调用 `POST /api/v1/auth/logout`
- **THEN** 成功后清理前端 auth bootstrap 状态
- **AND** 跳转到登录入口

### Requirement: Protected Writes Use Centralized CSRF Injection

logout 之外的受保护写请求 SHALL 通过统一前端 API 边界注入 `X-CSRF-Token`，而不是由页面组件各自拼装。

#### Scenario: Protected write uses centralized header injection

- **WHEN** 已登录用户发起受保护写请求
- **THEN** `apps/web/src/shared/api/` 统一注入 `X-CSRF-Token`
- **AND** 页面组件不手写该 header

### Requirement: Unauthorized And Forbidden UX

401 与 403 SHALL 在前端表现为不同语义。

#### Scenario: Unauthorized returns to login

- **WHEN** 受保护请求因 session 失效返回 401
- **THEN** 前端通过统一 unauthorized 收口清理登录态
- **AND** 回到未登录态或 `/login`

#### Scenario: Forbidden remains a permission error

- **WHEN** 已登录用户请求返回 403
- **THEN** 前端展示权限不足语义
- **AND** 不把该错误伪装成普通网络失败或 silent ignore

### Requirement: Front-End Auth Boundaries

前端登录接入 SHALL 遵守既有应用边界，避免把鉴权逻辑散落到页面组件。

#### Scenario: API calls stay in shared API

- **WHEN** 登录、bootstrap、logout 或受保护写请求需要访问后端
- **THEN** 调用收敛在 `apps/web/src/shared/api/`
- **AND** 页面组件不直接发起裸 `fetch`

#### Scenario: Runtime auth config stays in shared config

- **WHEN** 前端需要读取 `authEnabled` 或相关运行时配置
- **THEN** 读取收敛在 `apps/web/src/shared/config/`
- **AND** 组件不自行读取或解释环境变量

#### Scenario: Route and provider responsibilities remain separated

- **WHEN** 实现登录入口、受保护路由与 auth bootstrap
- **THEN** 路由页面放在 `apps/web/src/routes/`
- **AND** provider、router 和 layout 放在 `apps/web/src/app/`

### Requirement: Capability Status Is Visible Without Nav Gating

capability 初版 SHALL 作为状态展示存在，但不对当前主导航做强制裁剪。

#### Scenario: Navigation remains stable in v1 login integration

- **WHEN** 用户完成登录并进入管理台
- **THEN** 前端可以展示 actor 或 capability 状态
- **AND** 现有主导航不因 capability 缺失而被前端强制隐藏
- **AND** 后端 capability guard 仍是权限真源
