# Router Layout Specification

## MODIFIED Requirements

### Requirement: Dashboard Main Layout

应用 SHALL 提供统一的后台管理主布局，包含侧边栏导航、顶部面包屑和主体内容区域；同时登录入口必须与受保护管理台布局分离，并允许已登录但 capability 不足的用户进入统一受限态。

#### Scenario: Protected routes render within the dashboard shell

- **WHEN** 已登录且具备所需 capability 的用户访问受保护管理台路由
- **THEN** 左侧显示固定侧边栏，包含 Events、Runtime、Approvals、Plugins、Skills、Tools、Industries、Settings 导航入口
- **AND** 顶部显示面包屑导航，反映当前路由路径
- **AND** 主体区域渲染子路由内容

#### Scenario: Login route stays outside the dashboard shell

- **WHEN** 用户访问 `/login`
- **THEN** 页面不渲染受保护管理台侧边栏和面包屑
- **AND** 登录入口与后台壳保持分离

#### Scenario: Forbidden workspace route stays within the application shell semantics

- **WHEN** 已登录用户访问某个需要额外 capability 的 workspace 路由
- **AND** 当前 capability snapshot 不包含该 capability
- **THEN** 前端展示统一受限态
- **AND** 不把该场景退化成未登录跳转

#### Scenario: Navigation visibility follows the shared capability policy

- **WHEN** 应用为已登录用户渲染后台主导航
- **THEN** 每个导航入口的 visible / hidden 状态 SHALL 来自统一 capability policy
- **AND** 布局层不自行发明独立的导航权限规则

### Requirement: Route Placeholder Pages

应用 SHALL 为各导航入口创建页面入口，并通过统一路由策略区分公共登录页、可访问的受保护管理台页面和 capability 不足的受限页面。

#### Scenario: Protected placeholder pages require auth

- **WHEN** 开发者导航到 `/events`、`/runtime`、`/approvals`、`/plugins`、`/skills`、`/tools`、`/industries` 或 `/settings`
- **AND** 当前没有有效登录态
- **THEN** 前端跳转到 `/login`

#### Scenario: Login is a public route

- **WHEN** 用户访问 `/login`
- **THEN** 该路由不要求先具备管理台登录态
- **AND** 它作为公共登录入口存在

#### Scenario: Root route still lands in the dashboard entry flow

- **WHEN** 用户访问根路径 `/`
- **AND** 当前已登录且具备默认入口所需 capability
- **THEN** 根路径按默认首页流进入受保护管理台入口

#### Scenario: Login success restores original protected target

- **WHEN** 未登录用户访问受保护管理台目标路由并被重定向到 `/login`
- **AND** 用户成功登录
- **THEN** 前端恢复原目标路由而不是停留在登录页

#### Scenario: Direct login uses default dashboard entry flow

- **WHEN** 用户直接访问 `/login`
- **AND** 用户成功登录
- **THEN** 前端进入默认首页流

#### Scenario: Capability-limited route uses forbidden semantics after auth

- **WHEN** 已登录用户访问某个受保护管理台目标路由
- **AND** 该路由要求的 capability 不在当前 capability snapshot 中
- **THEN** 前端渲染统一受限页面或受限内容壳
- **AND** 不重定向到 `/login`
