## 1. OpenSpec Scope And Review Gate

- [x] 1.1 补齐 `web-debug-route-workbench` change 的 proposal、design、specs 和 tasks，覆盖 `/debug` 工作台、production 排除边界、页面状态收口方向和 AGENTS 规则更新要求。
- [x] 1.2 运行 `openspec validate web-debug-route-workbench --type change --strict --json`。
- [x] 1.3 创建 OpenSpec-only PR，并等待维护者明确评论“没问题”或批准后再进入实现。

## 2. Router Gating Boundary

- [x] 2.1 设计并实现开发态/生产态 router 装配分离，确保 production 不注册 `/debug`，也不导入 debug 页面模块。
- [x] 2.2 保持现有业务 file-route tree 继续服务正式路由，并为 debug subtree 提供开发态专用挂载路径。
- [x] 2.3 验证 `MainLayout` 正式导航不新增 `/debug` 入口，同时直接访问 debug 路径时仍使用现有布局壳层。

## 3. Debug Workbench Routes

- [x] 3.1 新增 `/debug` 根页，提供首批 4 个子路由的入口和边界说明。
- [x] 3.2 新增 `/debug/page-states`，集中承接页面级 loading、empty、overview/placeholder 等状态预览，并建立后续同类调试能力的统一入口。
- [x] 3.3 新增 `/debug/runtime-config`，展示前端已可见的 runtime config 解析结果和关键字段状态，不暴露敏感信息。
- [x] 3.4 新增 `/debug/error-fallback`，通过本地可控方式触发应用级错误 fallback，不依赖真实后端响应。
- [x] 3.5 新增 `/debug/route-playground`，验证 search params、未知状态值和 route fallback 行为。

## 4. Boundary Reinforcement

- [x] 4.1 更新 `apps/web/AGENTS.md`，明确新增本地调试能力优先进入 `/debug` 工作台，而不是继续散落在业务 route。
- [x] 4.2 收口本轮涉及的页面状态预览边界，明确后续新增同类预览不再默认挂到业务路由查询参数。

## 5. Validation

- [x] 5.1 在 `apps/web` 目录运行 `bun run lint`。
- [x] 5.2 在 `apps/web` 目录运行 `bun run build`。
- [x] 5.3 development 下手动检查 `/debug`、`/debug/page-states`、`/debug/runtime-config`、`/debug/error-fallback`、`/debug/route-playground`。
- [x] 5.4 验证 production build 中 `/debug` 不被注册，且产物不包含 debug route 入口和对应页面代码。
