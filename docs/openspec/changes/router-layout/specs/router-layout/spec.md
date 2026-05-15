# Router Layout Specification

## ADDED Requirements

### Requirement: TanStack Router Integration

项目 SHALL 使用 @tanstack/router-plugin Vite 插件实现基于文件系统的类型安全路由，并启用自动代码分割。

#### Scenario: Vite plugin configured

- **WHEN** 开发者检查 vite.config.ts
- **THEN** tanstackRouter 插件已配置，target 为 react，autoCodeSplitting 为 true

### Requirement: Router Context with Capability Placeholder

router context SHALL 包含 capabilities 字段，用于后续权限校验。当前阶段仅预留入口，不实现校验逻辑。

#### Scenario: Capability check placeholder exists

- **WHEN** 开发者检查 __root.tsx 的 beforeLoad
- **THEN** beforeLoad 中引用了 context.capabilities
- **AND** 不会因未实现校验而阻断路由

### Requirement: Dashboard Main Layout

应用 SHALL 提供统一的后台管理主布局，包含侧边栏导航、顶部面包屑和主体内容区域。

#### Scenario: Layout structure renders

- **WHEN** 应用加载任意路由
- **THEN** 左侧显示 240px 固定侧边栏，包含 Events、Runtime、Approvals、Plugins、Settings 导航入口
- **AND** 顶部显示面包屑导航，反映当前路由路径
- **AND** 主体区域渲染子路由内容

### Requirement: Route Placeholder Pages

应用 SHALL 为每个导航入口创建占位页面，提供页面标题、简介和功能分区描述。

#### Scenario: Placeholder pages exist

- **WHEN** 开发者导航到 /events、/runtime、/approvals、/plugins、/settings
- **THEN** 每个页面渲染对应标题和分区描述面板
- **AND** 根路径 / 重定向到 /events

### Requirement: Responsive Layout

布局 SHALL 在不同屏幕宽度下适配。

#### Scenario: Mobile adaptation

- **WHEN** 视口宽度 <= 760px
- **THEN** 侧边栏变为水平导航栏，面板网格变为单列

#### Scenario: Tablet adaptation

- **WHEN** 视口宽度在 761px - 1080px 之间
- **THEN** 面板网格显示为两列

### Requirement: Devtools Integration

开发环境 SHALL 集成 TanStackRouterDevtools。

#### Scenario: Devtools visible in development

- **WHEN** 开发者启动 dev server
- **THEN** 页面底部显示 TanStack Router Devtools 面板
