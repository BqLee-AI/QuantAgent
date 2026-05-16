# Tasks: 接入 Vitest Node Runner

## Task Graph

### Blocking Path

- [x] B1. 确认 `apps/web` 的 Vitest Node runner 边界与文件匹配规则
  - Input: issue #56、现有 `apps/web` 目录结构、#53/#54/#55/#8 的测试边界
  - Output: 明确使用 Node 环境、co-located `*.test.ts`、不承担浏览器与组件渲染测试
  - Write boundary: `openspec/changes/add-vitest-node-runner/proposal.md`, `specs/add-vitest-node-runner/spec.md`

- [x] B1.5. 固定 smoke test 目标文件
  - Input: `apps/web/src/shared/config/` 现有模块
  - Output: 选择 `apps/web/src/shared/config/runtime.ts` 作为 smoke test 目标，并预留 `apps/web/src/shared/config/runtime.test.ts`
  - Write boundary: `openspec/changes/add-vitest-node-runner/proposal.md`, `specs/add-vitest-node-runner/spec.md`, `tasks.md`

- [x] B2. 为 `apps/web` 接入 Vitest 并暴露标准命令
  - Input: `apps/web/package.json`、Vite/TypeScript 现有配置
  - Output: Vitest 依赖、独立 `vitest.config.ts`、`test:unit` / `test:unit:watch` scripts
  - Output: 确认 `tsconfig.app.json` 中的 `@/*` alias 在 Vitest 中可用，并与 `vite.config.ts` 的 `@` 解析保持一致
  - Write boundary: `apps/web/package.json`, `apps/web/vitest.config.*`, `apps/web/tsconfig*.json`（如需要）

- [x] B3. 添加最小 smoke test 并验证 co-located 规则生效
  - Input: `apps/web/src/shared/config/runtime.ts`
  - Output: `apps/web/src/shared/config/runtime.test.ts` 通过，证明命令、co-located 规则和 alias 配置工作正常
  - Write boundary: `apps/web/src/**`

- [x] B4. 文档化 unit runner 与其他测试层的职责边界
  - Input: issue #56、#53、#54、#55、#8 的职责描述
  - Output: 文档或 spec 说明 Vitest Node、Playwright、浏览器组件测试的边界，以及 #8/#55 对本 runner 的依赖
  - Write boundary: `openspec/changes/add-vitest-node-runner/**`, 相关说明文档（如实现阶段需要）

### Parallelizable Work

- [x] P2. 评估是否需要根脚本代理
  - Can start after: B2
  - Input: 根 `package.json`、现有 monorepo 命令约定
  - Output: 结论为本 change 仅要求 `bun --cwd apps/web run test:unit`，不新增根脚本代理
  - Write boundary: spec only unless implementation proves root script necessary

### Review Points

- [ ] R1. 审阅 spec 中关于测试边界、co-located `*.test.ts`、Axios adapter mock 的约束后，再进入实现。
- [x] R2. Vitest 配置和 smoke test 落地后，确认命令、glob 与现有前端构建配置不冲突。

## Verification

- [x] `bun --cwd apps/web run test:unit` 通过
- [x] `bun run lint` 通过
- [x] `bun run build --filter=web` 通过
- [x] `openspec validate add-vitest-node-runner --type change --strict --json` 通过
