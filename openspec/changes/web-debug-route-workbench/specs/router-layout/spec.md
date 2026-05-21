## MODIFIED Requirements

### Requirement: Dashboard Main Layout

应用 SHALL 提供统一的后台管理主布局，包含侧边栏导航、顶部面包屑和主体内容区域。

#### Scenario: Layout structure renders

- **WHEN** 应用加载任意已注册路由
- **THEN** 左侧显示固定侧边栏，包含 Events、Runtime、Approvals、Plugins、Skills、Tools、Industries、Settings 导航入口
- **AND** `/debug` 不出现在正式侧边导航中
- **AND** 顶部显示面包屑导航，反映当前路由路径
- **AND** 主体区域渲染子路由内容
