# Change: 接入 Vitest Node Runner

## Source

- GitHub issue: https://github.com/BqLee-AI/QuantAgent/issues/56
- Labels: `architecture`, `type:feature`, `priority:medium`, `status:needs-review`, `area:web`, `complexity:medium`
- State: OPEN

## Why

Issue `#53` 只提供 Playwright 浏览器测试基础设施，不能高效覆盖 `apps/web` 中的纯逻辑测试。#8 的 `ApiError`、`ErrorRegistry`、AxiosError 转换和 interceptor 行为测试，以及 #55 的 `mockEnvelope.ts` 纯数据测试，都需要一个轻量、快速、无浏览器依赖的 Node 级单元测试 runner。

当前仓库缺少这条测试链路，会导致：

- 纯 TypeScript 逻辑只能依赖浏览器测试间接覆盖，运行成本过高。
- #8 的 Tier 1 / Tier 2 自动化测试没有可落地的执行基础设施。
- #55 的 mock 数据构造无法用最小成本验证。
- 前端测试边界在 Vitest Node、Playwright、浏览器组件测试之间不够清晰。

## Problem

`apps/web` 当前没有 Node 环境 unit test runner，也没有统一的 unit test 命令、文件匹配规则和最小 smoke case。后续 issue 即使定义了测试要求，也缺少稳定的仓库级承载点。

## Goals

- 为 `apps/web` 接入 Vitest 作为 Node 环境单元测试 runner。
- 添加 `test:unit` 和 `test:unit:watch` 命令，并保证能在 `apps/web` 下直接运行。
- 统一纯逻辑测试文件放在被测文件旁边，使用 co-located `*.test.ts` 命名。
- 添加一个最小 smoke unit test，证明 runner、匹配规则和命令可用。
- 在文档中明确该 runner 支撑 #8 的 Tier 1 / Tier 2 测试，以及 #55 的 `mockEnvelope.ts` 测试。
- 明确 API Client interceptor 测试策略采用 Axios adapter mock，而不是 mock axios instance。

## Non-Goals

- 不负责 Playwright 浏览器测试；该范围由 #53 处理。
- 不封装 React Testing Library 或组件测试工具链；该范围由 #54 处理。
- 不实现 network mock 框架；该范围由 #55 处理。
- 不实现 API Client 本身；该范围由 #8 处理。
- 不要求渲染 React 组件。
- 不要求启动浏览器。

## Known Context

- `apps/web/package.json` 当前只有 `dev`、`build`、`lint`、`preview`，尚无单元测试命令。
- `apps/web/tsconfig.app.json` 已定义 `@/*` → `./src/*` 的 paths alias；`apps/web/vite.config.ts` 也通过 `resolve.alias` 手动把 `@` 指向 `./src`。
- 由于当前 alias 只有单个 `@`，Vitest 无需为此新增 `vite-tsconfig-paths` 依赖；在独立 `vitest.config.ts` 中手动保持同一条 `resolve.alias` 即可与现有导入约定对齐。
- 仓库已有 `openspec/changes/*` 结构，适合按 change 产出持久化 spec。
- `openspec/changes/api-client-error-governance/*` 已把 #56 作为依赖，但其中 Tier 2 测试策略需要统一为 Axios adapter mock。
- `apps/web/src` 当前代码以 `app/`、`routes/`、`shared/`、`styles/` 分层，适合使用被测文件旁边的 co-located 测试布局。

## What Changes

- 在 `apps/web` 添加 Vitest Node runner 所需开发依赖与配置文件。
- 使用独立 `apps/web/vitest.config.ts`，不把 Vitest 配置直接塞进 `vite.config.ts`。
- `vitest.config.ts` 采用最小 Node 测试配置，只保留 unit runner 需要的 `test` 与 `resolve.alias` 设置，不继承 `tanstackRouter`、`react`、`tailwindcss` 这些面向浏览器构建和开发服务器的 Vite 插件。
- 在 `vitest.config.ts` 中手动保持 `@` → `./src` 的 alias 映射，使其与 `tsconfig.app.json`、`vite.config.ts` 的现有导入约定一致。
- 在 `apps/web/package.json` 中增加 `test:unit`、`test:unit:watch` 命令。
- 配置测试文件匹配规则为 co-located `*.test.ts`，并显式排除 `node_modules`、`dist`、以及后续 Playwright 可能使用的 `tests/`、`e2e/` 目录，避免与 #53 冲突。
- 在 `apps/web/src/shared/config/runtime.ts` 旁添加 `apps/web/src/shared/config/runtime.test.ts` 作为最小 smoke test，直接验证已有纯函数 `loadRuntimeConfig()`。
- 在相关文档或 spec 中说明 Vitest Node、Playwright、浏览器组件测试的职责边界。
- 同步修正 #8 相关 spec 对 Tier 2 interceptor 测试策略的表述，使其与本 change 保持一致。

## Impact

- 影响目录：`apps/web/**`、`openspec/changes/add-vitest-node-runner/**`。
- 关联 spec：`openspec/changes/api-client-error-governance/specs/api-client-error-governance/spec.md`。
- 首个直接消费者是 #8：其 Tier 1 / Tier 2 API Client 测试需要先依赖本 runner 落地。
- #55 是后续消费者：`mockEnvelope.ts` 纯数据测试将在本 runner 就绪后复用这套基础设施。
- 受益 issue：#8、#55、后续所有前端纯逻辑测试需求。

## Dependencies And Risks

- 无明确前置依赖，可独立完成。
- 需要保持 Node 环境测试与浏览器测试职责边界清晰，避免把组件渲染需求误塞入本 runner。
- 需要确保 test file glob 不把浏览器测试或生成文件卷入 Vitest Node 执行范围。

## Open Questions

当前无阻塞实现的未决问题，结论如下：

- smoke test 目标固定为 `apps/web/src/shared/config/runtime.ts`，测试文件为 `apps/web/src/shared/config/runtime.test.ts`。该模块包含 `loadRuntimeConfig()` 及其依赖的纯逻辑校验函数，不依赖 DOM、React 或浏览器运行时，适合作为最小 smoke case。
- 不在仓库根 `package.json` 增加 `test:unit` 代理命令。当前根脚本只提供 `dev`、`build`、`lint` 等跨 workspace 的粗粒度入口，而 issue 56 的验收命令已经明确为 `bun --cwd apps/web run test:unit`；在仅有 `apps/web` 这一前端 workspace 的前提下，继续把 unit runner 命令内聚在 `apps/web` 更清晰，也避免过早引入一次性的根脚本约定。

## Success Criteria

- `bun --cwd apps/web run test:unit` 可以运行并通过。
- 可测试纯 TypeScript 逻辑模块，无需浏览器环境。
- 单元测试文件统一为 co-located `*.test.ts`。
- #8 和 #55 可明确引用该 runner 进行纯逻辑测试。
- API Client interceptor 测试策略在 spec 中明确为 Axios adapter mock。

## Verification

- `bun --cwd apps/web run test:unit`
- `bun run lint`
- `bun run build --filter=web`
