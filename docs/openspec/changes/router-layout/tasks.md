# Tasks: Router Layout

## 1. TanStack Router Plugin Integration

- [ ] 在 apps/web/package.json 中添加 @tanstack/router-plugin 开发依赖。
- [ ] 在 vite.config.ts 中配置 tanstackRouter 插件，启用 autoCodeSplitting。

## 2. Router Setup

- [ ] 创建 apps/web/src/app/router.tsx，定义 RouterContext（含 capabilities）并导出 router 实例。
- [ ] 更新 apps/web/src/main.tsx，使用 RouterProvider 替换直接渲染 App 组件。
- [ ] 删除 apps/web/src/App.tsx（已由路由系统接管）。

## 3. Main Layout

- [ ] 创建 apps/web/src/routes/__root.tsx，集成 MainLayout 和 TanStackRouterDevtools，在 beforeLoad 中预留 capability 校验。
- [ ] 创建 apps/web/src/app/layouts/MainLayout.tsx，包含 240px 侧边栏、面包屑导航和 Outlet。
- [ ] 添加 apps/web/src/styles.css，包含布局样式和响应式断点。

## 4. Route Placeholder Pages

- [ ] 创建 apps/web/src/routes/index.tsx，重定向到 /events。
- [ ] 创建 apps/web/src/routes/events/index.tsx 占位页。
- [ ] 创建 apps/web/src/routes/runtime/index.tsx 占位页。
- [ ] 创建 apps/web/src/routes/approvals/index.tsx 占位页。
- [ ] 创建 apps/web/src/routes/plugins/index.tsx 占位页。
- [ ] 创建 apps/web/src/routes/settings/index.tsx 占位页。

## 5. Verification

- [ ] 确认 `bun run build` 通过。
- [ ] 确认页面切换无整页刷新。
- [ ] 确认侧边栏高亮正确。
- [ ] 确认响应式布局适配。
