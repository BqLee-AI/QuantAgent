# Change: Router Layout

## Why

PR#37 已完成 Web 项目基座初始化（Vite + React + HeroUI），但应用尚无路由系统和后台管理布局。本 change 搭建基于 TanStack Router 的文件路由，并实现响应式后台主布局，为后续业务页面开发提供导航骨架。

## What Changes

- 集成 @tanstack/router-plugin Vite 插件，启用文件路由与自动代码分割。
- 创建 router context，预留 Capability 权限校验入口。
- 实现根路由，集成 TanStackRouterDevtools。
- 创建 MainLayout：240px 固定侧边栏导航 + 顶部面包屑 + 主体滚动区域。
- 创建路由占位页：Events、Runtime、Approvals、Plugins、Settings。
- 添加响应式布局样式，适配移动端与平板端。

## Out Of Scope

- WebSocket / 实时通道集成。
- 真实业务数据加载（TanStack Query 集成留给后续 issue）。
- 权限校验的具体实现（仅预留 beforeLoad 入口）。
- 页面内的组件实现（仅占位描述）。

## Success Criteria

- 页面切换无整页刷新，由客户端路由驱动。
- 侧边栏在当前路由下正确高亮。
- 布局在 760px / 1080px 断点下响应式适配。
- `bun run build` 通过。
