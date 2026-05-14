# 应用级错误边界与兜底错误页 Specification

## ADDED Requirements

### Requirement: Root-Level Error Boundary

应用 SHALL 在根部提供 React Error Boundary，用于捕获子树渲染阶段与同步生命周期阶段的异常，避免任一子树错误导致整页空白。

#### Scenario: Child subtree throws during render

- **WHEN** 某个已挂载子树在渲染过程中抛出异常
- **THEN** 应用 SHALL 切换到统一错误展示界面
- **AND** 页面 SHALL 保持可见而不是白屏

### Requirement: Unified Startup Fallback

应用 SHALL 为启动阶段提供统一兜底页，用于处理 runtime 配置加载失败、根组件初始化失败或路由壳初始化失败等问题。

#### Scenario: Bootstrap fails before app mounts

- **WHEN** 应用在挂载前发生错误
- **THEN** 应用 SHALL 渲染统一的启动失败兜底页
- **AND** 不应进入部分渲染状态

### Requirement: Minimal Error Display

错误页 SHALL 只展示必要的错误摘要；若错误上下文中存在 `request_id` 或 `trace_id`，可以一并展示。

#### Scenario: Error page receives contextual identifiers

- **WHEN** 错误上下文提供 `request_id` 或 `trace_id`
- **THEN** 错误页 SHALL 显示这些标识
- **AND** 错误页 SHALL 不显示敏感内部详情

### Requirement: Recovery Actions

错误页 SHALL 提供最小恢复入口：重新加载页面，以及返回首页或应用默认入口。

#### Scenario: User chooses recovery action

- **WHEN** 用户在错误页点击重新加载
- **THEN** 浏览器 SHALL 重新加载当前页面
- **WHEN** 用户在错误页点击返回首页
- **THEN** 应用 SHALL 导航到默认入口

### Requirement: Safe Error Disclosure

错误页 SHALL 默认避免暴露堆栈、密钥、环境变量或其他敏感信息。

#### Scenario: Unknown error is rendered

- **WHEN** 应用展示未知错误
- **THEN** 页面 SHALL 仅显示简短摘要和可选的错误标识
- **AND** 不应直接展示完整堆栈或内部配置

