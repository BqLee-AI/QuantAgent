# apps/web Review Overview

本文件是 `apps/web` 变更的 AI Code Review 索引。先用 changed files 和 diff 识别场景，再加载对应细则。

现有代码只能作为迁移背景，不是规范来源。审查新增或被修改代码时，以 `architecture-principles.md`、`apps/web/AGENTS.md`、设计文档和前端主流分层实践作为目标边界。

主要真源：

- `apps/web/AGENTS.md`
- `docs/design/09-frontend-architecture-design.md`
- `docs/design/08-api-and-websocket-design.md`
- `.agents/skills/references/engineering-quality-gate.md`
- `.agents/skills/references/web-architecture-gate.md`
- `architecture-principles.md`

## 场景索引

| 场景 | 触发信号 | 未来细则 | 核心审查问题 |
| --- | --- | --- | --- |
| 架构基准 | 任意 `apps/web/**` 变更 | `architecture-principles.md` | 是否按目标分层审查，而不是把当前不规范代码当模板 |
| 文件职责与 feature 结构 | 新增 feature、复杂 route、目录增长、shared 能力、diff 同时改 api/query/hook/component/types/README | `.agents/skills/references/web-file-responsibility-and-feature-structure.md` | 是否能按文件名定向阅读；是否拆到 route、api、contracts、query keys、queries、mutations、business hooks、components、types、utils、README |
| API 与 TanStack Query | `src/shared/api/**`、`src/features/**/api/**`、`src/features/**/queries/**`、diff 出现 `apiClient` / `fetch` / `ApiResponse` / `code/data/msg/error` | `api-and-query.md` | 是否绕过 feature API / query 层直接请求；是否手写 envelope；query key、mutation invalidation、request id 和错误 UI 是否稳定 |
| Route 与 layout | `src/routes/**`、`src/app/router.tsx`、`src/app/layouts/**`、`src/routeTree.gen.ts` | `routes-and-layout.md` | route 是否保持薄层；公开页和后台 shell 是否分离；权限、redirect、search params、生成路由是否符合边界 |
| 组件与业务 Hook | `src/features/**/components/**`、`src/features/**/hooks/**`、`src/shared/ui/**`、`src/app/components/**` | `components-and-business-hooks.md` | 组件是否按 feature/shared 边界放置；props 是否稳定；复杂状态、请求、权限和 JSX 是否通过业务 hook 与展示组件拆分 |
| 权限与敏感信息 | `src/shared/auth/**`、login、approval、plugin config、runtime detail、capability 相关改动 | `auth-permission-and-security.md` | 前端是否绕过后端权限；secret、prompt、私有策略、交易细节、tool args 是否脱敏 |
| 实时状态同步 | WebSocket、realtime、polling、query invalidation、runtime 状态页面 | `realtime-and-state-sync.md` | WebSocket 是否只做状态提醒；REST 是否仍是快照真源；reconnect 和局部 patch 是否有校准策略 |
| 表单与插件配置 | settings、approval action、plugin config form、schema-driven form、Zod schema | `forms-and-plugin-config.md` | 插件配置是否 schema-driven；敏感字段是否 masked；validate/save/invalidate/audit 状态是否完整 |
| 状态视图 | 新页面、列表、详情、操作按钮、toast、error boundary、空态/加载态 | `error-loading-empty-states.md` | loading、empty、error、permission denied 是否覆盖；request id / trace id 是否可排查 |
| 样式与设计系统 | CSS、Tailwind token、HeroUI theme、layout、页面视觉结构 | `styling-and-design-system.md` | 是否优先 HeroUI 和 Tailwind token；是否保持管理台密度；是否出现营销 hero、卡片套卡片、文本溢出 |
| 测试与 debug | `src/test/**`、debug route、mock envelope、provider hooks、runtime config | `tests-and-debug-tools.md` | 变更是否有匹配验证；debug route 是否不进入生产；fixture 是否避免真实 secret |

## 选择规则

- 只改 `*.module.css` 或视觉 token 时，优先审查样式与状态视图，不应自动套用 API finding。
- route 中出现裸 `apiClient.get(...)`、`fetch(...)` 或 envelope 解析时，必须审查 API 与 TanStack Query 场景。
- 新增 feature、复杂 route 或目录重组时，必须审查文件职责与 feature 结构场景。
- 新增共享组件时，必须审查组件边界；复杂、跨域或非显然组件目录必须要求 README / usage note。
- 目录下如果平铺大量组件、hooks、types 或 helper 文件，应额外审查是否需要按职责分组。
- 修改 auth、approval、plugin config 或 runtime detail 时，必须额外审查敏感信息和权限边界。
- 修改旧的不规范区域但只改文案或样式时，不强制要求顺手重构；如果继续追加业务请求、状态或权限逻辑，应按扩大债务处理。

## 初始 finding 倾向

优先报告这些问题：

- 页面、route 或组件直接裸调 API，绕过 feature query / mutation。
- route 文件承担业务请求、复杂状态和 JSX 大量混写。
- 403、后端错误或操作失败没有 request id / trace id。
- UI 展示 secret、完整 prompt、私有策略或完整模型推理链。
- WebSocket payload 被当成长期业务状态真源。
- 复杂目录无 README、无中文边界注释、无子目录分组，导致 AI 和 reviewer 无法快速定向定位。

## 已落地细则

- `architecture-principles.md`
- `.agents/skills/references/web-file-responsibility-and-feature-structure.md`
- `api-and-query.md`
- `routes-and-layout.md`
- `components-and-business-hooks.md`

其余场景暂时只保留索引，后续按 #166 逐步细化。
