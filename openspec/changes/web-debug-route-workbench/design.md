## Context

issue #99 要求为前端建立开发态专用 `/debug` 路由工作台，并固定首批 4 个调试子路由：页面状态、runtime config、错误兜底和 route playground。当前 `apps/web` 使用 TanStack Router 的文件路由和生成的 `src/routeTree.gen.ts`，`createAppRouter()` 直接静态使用该 route tree；现有开发态 gating 只有 `__root.tsx` 中的 `import.meta.env.DEV` devtools 条件渲染，没有现成的 debug route 装配边界。

issue 明确要求 production build 不仅不能访问 `/debug`，还不能把 debug route 与页面代码打入产物。与此同时，issue 评论要求同步更新 `apps/web/AGENTS.md`，让 AI 和开发者都知道后续新增调试能力优先进入 `/debug` 工作台，而不是继续散落在业务 route 中。

## Goals / Non-Goals

**Goals:**

- 建立开发态专用 `/debug` 根入口和固定 4 个子路由。
- 通过编译时 gating 让 production 不注册 `/debug`，也不打包 debug 页面代码。
- 把页面级状态预览收口到 `/debug/page-states`，建立后续同类调试能力的落位规则。
- 为 runtime config、错误兜底和 route fallback 提供统一、可重复、本地可控的调试视图。
- 保持 `/debug` 不进入正式侧边导航，不演变成公开后台或业务功能。

**Non-Goals:**

- 不在本轮实现通用开发工具大全、API 调试器、鉴权模拟器、插件调试台或业务数据回放系统。
- 不在本轮暴露真实 secret、token、私有策略、完整模型推理链或敏感运行时细节。
- 不用 `/debug` 替代 Vitest、Playwright、Storybook 或组件文档系统。
- 不要求一次性迁完所有历史调试入口，但需要建立“后续统一收口”的明确规则。

## Decisions

### 1. `/debug` 使用开发态专用路由装配，不走常驻文件路由

当前 `apps/web` 的业务路由来自静态生成的 `src/routeTree.gen.ts`。如果把 `/debug` 直接做成普通文件路由，route tree 会在构建时静态导入 debug route 模块，即使页面内部再用 `import.meta.env.DEV` 隐藏，也无法满足“production 不包含 debug 页面代码”的要求。

因此 `/debug` 采用“业务 route tree + 开发态附加 debug subtree”的装配方案：业务路由继续由现有 file-based route tree 承接，debug 路由改为单独的开发态模块，并只在 dev build 的 router 装配路径中被导入和挂载。production router 只使用业务 route tree，不导入 debug 模块。

替代方案是让 `/debug` 继续走文件路由，再在页面或导航层做 `import.meta.env.DEV` 条件渲染。该方案只能隐藏入口，不能阻止 debug route 和页面代码进入产物，因此不采用。

### 2. `/debug` 根页是索引页，不进入正式导航

`/debug` 需要一个根目录页，承担子路由索引、用途说明和边界提醒的作用，避免调试入口再次依赖“记忆具体路径”。该页面直接挂在现有后台主布局内，允许通过 URL 直接访问，但不加入 `MainLayout` 的 `navItems` 正式导航列表。

替代方案是不给 `/debug` 根页，只保留若干隐式子路由。该方案会降低可发现性，也会让新增 debug 子路由再次回到“知道路径的人才会用”的状态，因此不采用。

### 3. `/debug/page-states` 成为页面状态预览的统一收口入口

现有页面级 `loading` / `empty` 预览已经开始出现在业务路由查询参数中。如果不在这一轮明确收口，后续同类调试能力会继续散落在业务 route。`/debug/page-states` 负责集中展示页面级 loading、empty、overview/placeholder 等状态，并作为后续新增页面状态预览的默认入口。

这并不要求本轮立刻迁完所有历史入口，但要求在 OpenSpec、AGENTS 和实现边界中明确：新增同类预览优先进入 `/debug/page-states`，而不是继续在业务 route 上增加临时 query 参数。

替代方案是把 `/debug/page-states` 仅做成静态示例页，继续允许业务路由自由挂预览参数。该方案无法解决 issue 的长期边界问题，因此不采用。

### 4. `/debug/runtime-config` 只展示前端已可见配置

`loadRuntimeConfig()` 当前只解析 `apiBaseUrl`、`websocketUrl`、`mode` 和 `authEnabled`。`/debug/runtime-config` 只允许展示这类前端已可见、已解析的配置结果和关键字段状态，不新增任何 secret、token 或后端私有配置读取。

替代方案是直接展示更完整的运行时环境变量快照。该方案会放大敏感信息泄露风险，也违反仓库对前端敏感信息脱敏展示的规则，因此不采用。

### 5. `/debug/error-fallback` 用受控异常触发应用级 fallback

`/debug/error-fallback` 的目标是验证当前应用级错误边界和恢复路径，而不是制造真实后端错误。页面通过本地可控方式触发受控异常，使开发者能稳定看到 fallback 页面、确认恢复动作和安全展示行为。

替代方案是依赖真实请求失败或手动改代码来触发错误边界。该方案不可重复，也会把调试成本继续留在零散手工操作中，因此不采用。

### 6. `/debug/route-playground` 专门验证 search params 与 fallback 行为

`/debug/route-playground` 用于本地验证 search params、未知状态值和 route fallback 语义，不依赖真实业务接口。它承担 route-level 调试实验位，避免这类调试逻辑继续留在正式业务 route 内。

替代方案是把这类调试逻辑继续内嵌进各业务页面。该方案正是 issue 想要阻止的扩散路径，因此不采用。

### 7. `apps/web/AGENTS.md` 必须补充 `/debug` 收口规则

issue 评论已经要求更新 web 层 AGENTS，这不是可选文档润色，而是长期控制面变更。规则需要明确：新增本地调试页面、状态预览、route playground 或类似开发态入口时，优先进入 `/debug` 工作台；不继续在业务 route 加临时按钮、query 参数或局部 hack，除非有明确真源批准作为正式功能保留。

## Risks / Trade-offs

- [Risk] TanStack Router 的当前 file-route 生成方式不支持直接把 `/debug` 干净排除出 production 产物。
  → Mitigation: 设计阶段就把 debug subtree 从常驻 file-route tree 中拆开，采用独立开发态装配模块，而不是实现后再补救。

- [Risk] 历史页面状态预览仍然暂时留在业务路由里，团队可能误以为这种模式仍被允许继续扩展。
  → Mitigation: 在 OpenSpec requirement 和 `apps/web/AGENTS.md` 中显式写出新增同类预览必须优先进入 `/debug/page-states`。

- [Risk] `/debug/runtime-config` 被误扩展为“环境变量浏览器”。
  → Mitigation: requirement 限定只展示前端已解析且本就可见的配置字段，不新增敏感环境变量透出。

- [Risk] `/debug/error-fallback` 可能被实现成依赖真实 API 错误的脆弱演示。
  → Mitigation: requirement 明确它必须使用本地可控方式触发 fallback，不依赖后端响应。

- [Risk] `/debug` 页面虽然不在导航里，但如果构建验证不足，仍可能意外进入 production 包。
  → Mitigation: tasks 和验收中要求 production 验证不仅检查路由不可达，也检查产物不包含 debug route 入口与页面代码。

## Migration Plan

1. 新建并评审本 change 的 OpenSpec artifacts。
2. 在实现阶段先完成开发态/生产态 router 装配分离，再增加 `/debug` 根页和 4 个子路由。
3. 同步更新 `apps/web/AGENTS.md`，把 `/debug` 收口规则固化为长期边界。
4. 通过 development 手动检查与 production build 验证确认 `/debug` 只存在于开发态。

## Open Questions

- 无。issue 对首批 4 个子路由、production 排除口径和 `/debug/page-states` 收口方向已经足够明确，本 change 直接按这些约束实施。
