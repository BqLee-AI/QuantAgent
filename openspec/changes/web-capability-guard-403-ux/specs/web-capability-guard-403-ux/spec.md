# Web Capability Guard And 403 UX Specification

## ADDED Requirements

### Requirement: Shared Capability Policy

`apps/web` SHALL 提供统一的 capability policy 边界，供路由、导航和页面操作入口复用，而不是由页面组件各自维护 capability 字符串判断。

#### Scenario: Shared policy is the only capability mapping source

- **WHEN** 前端需要判断某个 workspace 路由、导航入口或高风险操作是否可访问
- **THEN** 判断来源于统一 capability policy
- **AND** 页面组件不直接散落硬编码 capability 字符串

#### Scenario: Navigation state is derived from the shared policy

- **WHEN** 前端决定某个导航入口应显示、隐藏或禁用
- **THEN** 该结果来源于统一 capability policy
- **AND** 页面或布局层不自行定义另一套隐藏或禁用规则

### Requirement: Capability-Aware Route Semantics

前端 SHALL 区分未登录与已登录但 capability 不足两类访问失败语义。

#### Scenario: Anonymous user still follows login redirect

- **WHEN** 未登录用户访问受保护 workspace 路由
- **THEN** 前端跳转到 `/login`
- **AND** 不把 capability guard 当成该场景的主要处理路径

#### Scenario: Authenticated user with missing capability sees forbidden route state

- **WHEN** 已登录用户访问需要特定 capability 的 workspace 路由
- **AND** 当前 capability snapshot 不包含所需 capability
- **THEN** 前端展示统一的受限路由语义
- **AND** 不重定向回 `/login`

### Requirement: Navigation And Entry Visibility Policy

前端 SHALL 为主导航、页面入口和高风险操作提供统一的 capability 可见性策略。

#### Scenario: Fully inaccessible route entry uses hidden state

- **WHEN** 某个 workspace 页面入口在当前 capability snapshot 下完全不可访问
- **THEN** 该入口 SHALL 根据统一 policy 进入 hidden 状态
- **AND** 隐藏规则不由页面各自决定

#### Scenario: High-risk action uses disabled-with-reason state

- **WHEN** 当前 capability 不足以执行高风险操作
- **THEN** 前端 SHALL 保留该操作入口的 disabled 状态并提供原因说明
- **AND** UI 提供明确原因而不是等用户点击后再静默失败

### Requirement: Unified Forbidden Experience

前端 SHALL 为 403 权限不足提供统一体验，而不是把 403 退化成普通网络错误。

#### Scenario: Page-level forbidden state shows permission semantics

- **WHEN** 页面级访问因 capability 不足而失败
- **THEN** 用户看到明确的权限不足说明
- **AND** UI 提供返回入口或恢复动作

#### Scenario: Operation-level forbidden state preserves shared error semantics

- **WHEN** 局部高风险操作返回 403
- **THEN** 前端复用共享 API error 语义展示权限不足
- **AND** 不把该失败伪装成 silent ignore 或普通网络异常

### Requirement: Forbidden Diagnostics Are User-Visible

页面级或操作级 403 SHALL 提供稳定的排查信息入口。

#### Scenario: Forbidden view can access request and trace metadata

- **WHEN** shared API client 返回包含 `request_id` 或 `trace_id` 的 403 错误
- **THEN** 前端受限态或权限提示 SHALL 提供这些字段的可见入口
- **AND** 不泄露 session cookie、password、secret 或其他敏感值

### Requirement: Back-End Guard Remains The Source Of Truth

前端 capability policy SHALL 只负责 UX 与误操作预防，不能替代后端权限校验。

#### Scenario: UI gating does not replace back-end enforcement

- **WHEN** 前端根据 capability policy 隐藏或禁用某个入口
- **THEN** 后端 capability guard 仍必须保护对应资源或操作
- **AND** 前端仍必须正确处理后端返回的 403
