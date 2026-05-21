## Why

当前前端的页面状态预览、runtime config 解析、错误兜底和 route fallback 调试入口分散在业务路由查询参数、临时按钮或局部 hack 中，缺少统一、稳定、可发现的开发态入口。issue #99 现在要先把这些调试能力收敛到一个明确边界的 `/debug` 工作台里，避免继续污染正式业务 route，并建立 production 完全排除 debug 路由与代码的长期约束。

## What Changes

- 为 `apps/web` 新增开发态专用 `/debug` 路由工作台和根目录页，提供统一调试入口说明。
- 固定首批 4 个调试子路由：`/debug/page-states`、`/debug/runtime-config`、`/debug/error-fallback`、`/debug/route-playground`。
- 定义 `/debug` 的编译时 gating 边界：production build 不注册 `/debug`，也不包含其子路由和对应调试页面代码。
- 明确 `/debug/page-states` 作为后续页面级状态预览的统一收口入口，避免新的调试预览继续散落在业务 route 查询参数里。
- 明确 `/debug/runtime-config` 只能展示前端已可见的 runtime config 解析结果，不暴露 secret、token 或敏感运行时细节。
- 明确 `/debug/error-fallback` 和 `/debug/route-playground` 只提供本地可控、可重复的调试视图，不依赖真实后端返回。
- 更新 `apps/web/AGENTS.md`，补充“新增本地调试能力优先进入 `/debug` 工作台，而不是继续留在业务 route” 的长期规则。

## Capabilities

### New Capabilities
- `web-debug-route-workbench`: 定义开发态 `/debug` 路由工作台、首批调试子路由、production 排除边界与后续 debug 能力收口规则。

### Modified Capabilities
- `router-layout`: 更新后台主布局 requirement，明确 `/debug` 不进入正式侧边导航，同时保留直接访问 debug 路径时的路由壳与面包屑行为。

## Impact

- `apps/web/src/app/router.tsx`、`apps/web/src/routes/**`、`apps/web/src/routeTree.gen.ts` 相关的路由装配和开发态 gating 边界。
- `apps/web/src/app/layouts/MainLayout.tsx` 的导航与面包屑契约。
- `apps/web/src/shared/config/runtime.ts` 的前端可见配置展示边界。
- `apps/web/AGENTS.md` 的长期协作规则。
- 后续页面状态预览、route fallback 调试和错误兜底验证的落位规则。
