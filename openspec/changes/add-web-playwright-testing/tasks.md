# Tasks: 接入 Web Playwright 浏览器测试基础设施

## Task Graph

### Blocking Path

- [x] B1. 固定浏览器测试边界、目录分层与首轮浏览器矩阵
  - Input: issue #53、用户确认结论、现有 `apps/web` 与 `add-vitest-node-runner` change 的测试边界
  - Output: 明确 Chromium-only、CI/CD 暂不纳入、Playwright Component Testing 启用、Vitest Node 与浏览器测试职责分离
  - Output: 明确页面级 E2E 用例放在 `apps/web/e2e/`，CT 用例放在 `apps/web/tests/components/`
  - Write boundary: `openspec/changes/add-web-playwright-testing/proposal.md`, `specs/web-playwright-testing/spec.md`

- [x] B2. 为 `apps/web` 接入 Playwright 基础配置与标准命令
  - Input: `apps/web/package.json`、`apps/web/vite.config.ts`、当前前端 dev server 约定
  - Output: Playwright 依赖、配置文件、`test:e2e` / `test:e2e:ui` / `test:e2e:debug` 等命令
  - Output: 使用 Bun 生态完成本地 Chromium 浏览器安装，例如 `bunx playwright install chromium`；Linux 环境可按需追加 `--with-deps`
  - Write boundary: `apps/web/package.json`, `apps/web/playwright*.config.*`, `apps/web/tsconfig*.json`（如需要）

- [x] B2.5. 验证 E2E 启动策略与当前 Vite 启动方式兼容
  - Input: `apps/web` 当前 `dev` script 为 `vite`、固定端口 `5173`、本地 E2E 启动方案
  - Output: 确认 `bun --cwd apps/web run dev -- --host 127.0.0.1 --port 5173` 是否可用；若不可用，则切换到 Bun 生态内的本地包装脚本或等效方案
  - Output: 确认 E2E 命令能等待本地 server 就绪、复用已存在的本地 server，并在 Windows 上正常退出
  - Write boundary: `apps/web/playwright*.config.*`, `openspec/changes/add-web-playwright-testing/**`

- [x] B3. 建立 Chromium smoke test 与报告/诊断策略
  - Input: `apps/web/src/routes/__root.tsx`, `apps/web/src/routes/events/index.tsx`，以及 `Event Inbox` / `Events` 稳定文案
  - Output: 至少一个真实浏览器 smoke test，验证 `.page-title` 的 `Events` 或 `.page-kicker` 的 `Event Inbox` 已渲染；配置 HTML report 与失败时诊断产物保留策略
  - Write boundary: `apps/web/e2e/**`, `apps/web/test-results/**`（运行产物）, Playwright config

- [x] B4. 启用 Playwright Component Testing 基础承载
  - Input: #54 对浏览器组件测试的依赖、现有 Vite/React 工程结构
  - Output: 可供后续组件测试直接接入的基础配置、目录约定与最小入口，不包含组件测试 helper 封装
  - Output: 验证 CT 是否可直接复用现有 Vite 配置；若路由插件冲突，则收敛为独立 CT Vite 配置并保持 `@` alias 一致
  - Write boundary: `apps/web/playwright*.config.*`, `apps/web/tests/components/**`, 说明文档

- [x] B5. 文档化三层测试边界与本地调试方式
  - Input: #53、#54、#55、已归档 `add-vitest-node-runner` change
  - Output: 文档或说明中明确 Vitest Node、Playwright E2E、Playwright Component Testing 的职责边界、命令和目录约定
  - Write boundary: `apps/web/README.md` 或测试说明文档, `openspec/changes/add-web-playwright-testing/**`

### Parallelizable Work

- [x] P1. 预留 route mock 目录扩展点
  - Can start after: B2
  - Input: #55 对 Playwright route mock 的依赖
  - Output: 明确 route mock 推荐目录或辅助文件落点，但不实现 mock helper
  - Write boundary: spec/doc only unless implementation requires placeholder files

### Review Points

- [x] R1. 审阅 spec 中关于 Chromium-only、CI 延后、Component Testing 启用与测试边界的约束后，再进入实现。
- [x] R2. Playwright 配置与目录约定落地后，确认其不会与现有 Vitest unit test glob 冲突。

## Verification

- [x] `bun run --cwd apps/web test:ct` 通过
- [x] `bun run --cwd apps/web test:e2e` 通过
- [x] `bun run --cwd apps/web test:e2e:ui` 可启动 Playwright UI 模式
- [x] Chromium 浏览器二进制已通过 `bunx playwright install chromium` 或等效 Bun 命令安装可用；Linux 环境可按需追加 `--with-deps`
- [x] `bun run lint` 通过
- [x] `bun run build --filter=web` 通过
- [x] `openspec validate add-web-playwright-testing --type change --strict --json` 通过
