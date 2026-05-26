## MODIFIED Requirements

### Requirement: Route Placeholder Pages

应用 SHALL 为每个导航入口创建占位页面，提供页面标题、简介和功能分区描述；根路径 `/` SHALL 进入独立 Dashboard 默认首页流，而不是直接重定向到 `/events`。

#### Scenario: Placeholder pages exist
- **WHEN** 开发者导航到 `/events`、`/runtime`、`/approvals`、`/plugins`、`/skills`、`/tools`、`/industries` 或 `/settings`
- **THEN** 每个页面渲染对应标题和分区描述面板

#### Scenario: Root route lands in the dashboard home flow
- **WHEN** 用户访问根路径 `/`
- **THEN** 根路径进入独立 Dashboard 首页流
- **AND** 不直接把 `/events` 当作默认首页替代路径
