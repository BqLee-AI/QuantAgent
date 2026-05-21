## ADDED Requirements

### Requirement: Development-Only Debug Workbench Entry

Web 应用 SHALL 提供一个开发态专用的 `/debug` 路由工作台，作为本地调试能力的统一入口。

#### Scenario: Debug root page is available in development

- **WHEN** 开发者在 development 环境访问 `/debug`
- **THEN** 应用渲染 debug 工作台根页
- **AND** 根页展示首批调试子路由入口和用途说明

#### Scenario: Debug root page stays out of formal navigation

- **WHEN** 开发者检查主侧边导航
- **THEN** `/debug` 不出现在正式导航入口中
- **AND** 直接访问 `/debug` 时仍使用现有应用布局壳层

### Requirement: Fixed First-Batch Debug Subroutes

`/debug` 首批 SHALL 固定提供 `page-states`、`runtime-config`、`error-fallback`、`route-playground` 四个子路由。

#### Scenario: All first-batch routes exist in development

- **WHEN** 开发者在 development 环境检查 `/debug` 工作台
- **THEN** `/debug/page-states`、`/debug/runtime-config`、`/debug/error-fallback`、`/debug/route-playground` 都可访问
- **AND** 本轮不要求额外扩展更多 debug 子路由

### Requirement: Production Excludes Debug Routes And Code

production build SHALL 不注册 `/debug` 路由，并且不包含 debug 工作台及其页面代码。

#### Scenario: Production router does not expose debug paths

- **WHEN** 应用以 production 构建运行
- **THEN** `/debug` 及其子路由不可访问
- **AND** production router 中不存在 debug route 入口

#### Scenario: Production bundle excludes debug page modules

- **WHEN** 开发者验证 production 构建产物
- **THEN** 产物中不包含 debug 工作台页面模块
- **AND** 不允许仅靠运行时隐藏来满足该 requirement

### Requirement: Page State Debugging Is Centralized

`/debug/page-states` SHALL 成为页面级状态预览的统一开发态入口。

#### Scenario: Page state workbench covers common page-level states

- **WHEN** 开发者访问 `/debug/page-states`
- **THEN** 页面可受控预览页面级 loading、empty 和 overview/placeholder 等状态
- **AND** 这些预览不依赖真实后端返回

#### Scenario: New page-state previews prefer the debug workbench

- **WHEN** 后续新增页面级状态预览能力
- **THEN** 新能力优先进入 `/debug/page-states`
- **AND** 不应继续默认散落在业务 route 的临时查询参数或按钮中

### Requirement: Runtime Config Debug View Is Safe

`/debug/runtime-config` SHALL 仅展示前端已可见的 runtime config 解析结果和关键字段状态。

#### Scenario: Runtime config page shows parsed public config only

- **WHEN** 开发者访问 `/debug/runtime-config`
- **THEN** 页面展示前端运行时可见的配置解析结果
- **AND** 页面不依赖真实后端响应

#### Scenario: Runtime config page does not disclose secrets

- **WHEN** runtime config 调试页渲染配置内容
- **THEN** 页面不得显示 secret、token 原文、私有策略或其他敏感运行时细节

### Requirement: Error Fallback Debug View Uses Controlled Trigger

`/debug/error-fallback` SHALL 提供本地可控的方式触发应用级错误 fallback。

#### Scenario: Debug page triggers fallback without backend dependency

- **WHEN** 开发者在 `/debug/error-fallback` 执行受控触发动作
- **THEN** 应用进入统一错误 fallback 展示路径
- **AND** 该路径不依赖真实后端错误响应

#### Scenario: Fallback debug view preserves safe disclosure boundary

- **WHEN** 错误 fallback 页面被触发
- **THEN** 页面继续遵守应用级错误展示的安全边界
- **AND** 不直接暴露堆栈、环境变量或敏感内部详情

### Requirement: Route Playground Reproduces Route-Level Fallbacks

`/debug/route-playground` SHALL 提供本地可控的 route-level 调试视图，用于验证 search params、未知状态值和 fallback 行为。

#### Scenario: Route playground validates route state branches locally

- **WHEN** 开发者访问 `/debug/route-playground`
- **THEN** 页面可以本地复现 search params 和 route fallback 的目标场景
- **AND** 不依赖真实业务 API 返回

### Requirement: Debug Workbench Has Explicit Admission Boundary

`/debug` 工作台 SHALL 只承接开发态本地调试能力，不承接正式业务功能或敏感诊断面板。

#### Scenario: Debug capability stays within development boundary

- **WHEN** 开发者为前端新增本地调试入口
- **THEN** 可以把页面状态预览、route playground、runtime config 可视化等能力纳入 `/debug`
- **AND** 不应把真实业务流程、权限绕过、敏感信息展示或运营后台功能纳入 `/debug`
