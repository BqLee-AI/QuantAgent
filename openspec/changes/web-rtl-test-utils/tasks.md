# Tasks: React Testing Library 测试工具封装

## 任务图

### 串行阻塞项

1. 确认 #53 的 CT 基础设施和当前测试边界。
   - 输入：`apps/web/playwright-ct.config.ts`、`apps/web/README.md`、`openspec/specs/web-playwright-testing/spec.md`。
   - 输出：确认本 change 只补 RTL helper，不重做 E2E/CT runner。
   - 写入边界：无。

2. 固化 `AppProviders` 必传 props 与默认值策略。
   - 输入：`apps/web/src/app/providers.tsx`、`apps/web/src/shared/config/**`。
   - 输出：确认 `AppProviders` 要求 `config` 和 `queryClient` 两个必传 prop；`renderWithProviders` 内部使用 `createAppQueryClient()` 创建独立 QueryClient；定义 test-safe 默认 RuntimeConfig 为 `{ apiBaseUrl: '', websocketUrl: '', mode: 'test', authEnabled: false }`。
   - 写入边界：无。

3. 添加 RTL 相关依赖。
   - 输入：当前 `apps/web/package.json`。
   - 输出：`@testing-library/react`、`@testing-library/jest-dom`、`@testing-library/user-event` 作为 web devDependencies。
   - 写入边界：
     - `apps/web/package.json`
     - `apps/web/bun.lock`

4. 接入 CT 测试 setup。
   - 输入：`playwright-ct.config.ts` 和 Playwright CT setup 约定。
   - 输出：通过 `apps/web/tests/components/setup.ts` 接入 jest-dom matcher 与 RTL cleanup，并在 `playwright-ct.config.ts` 中引用，使其只作用于 CT 环境。
   - 写入边界：
     - `apps/web/playwright-ct.config.ts`
     - `apps/web/tests/components/setup.ts`

5. 创建 `src/test/` 测试工具目录。
   - 输入：当前 `apps/web/src` 目录。
   - 输出：`apps/web/src/test/` 存在，用于承载测试公共工具。
   - 写入边界：`apps/web/src/test/`。

6. 创建测试公共入口。
   - 输入：`AppProviders`、RuntimeConfig 类型、RTL API。
   - 输出：`apps/web/src/test/render.tsx`，包含 `renderWithProviders` 和统一测试导出。
   - 写入边界：`apps/web/src/test/render.tsx`。

7. 使用 helper 新增最小组件测试。
   - 输入：`PlaceholderPanel` 与 `renderWithProviders`。
   - 输出：保留现有 `placeholder-panel.spec.tsx` Playwright `mount` 测试，新建 `placeholder-panel-rtl.spec.tsx` 作为 RTL helper proof。
   - 写入边界：`apps/web/tests/components/placeholder-panel-rtl.spec.tsx`。

8. 验证并更新测试说明。
   - 输入：实现后的测试命令和文档。
   - 输出：验证结果；如测试导入约定变化，同步 README。
   - 写入边界：`apps/web/README.md`，仅在约定变化时更新。

### 可并行项

- 在完成阻塞项 1 和 2 后，依赖添加与 README 更新可并行准备，因为写入边界不同。
- CT setup 与 `renderWithProviders` 需要串行对齐，避免 matcher/cleanup 生命周期重复或缺失。
- 最小组件测试必须在 helper API 确认后开始。

### 审核点

- 本 spec 创建后、任何 `apps/web` 代码改动前，需要人工审核。
- `renderWithProviders` 公共 API 定稿前，需要确认是否继续排除 QueryClient 自定义接口。
- 实现后如果 RTL 与 Playwright CT 的生命周期出现冲突，需要回看 design 再调整。

## 清单

- [x] 创建 issue #54 的 OpenSpec change。
- [x] 确认 #53 的 CT 基础设施和当前测试边界。
- [x] 固化 `AppProviders` 必传 props 与默认值策略。
- [x] 添加 RTL 相关依赖。
- [x] 通过 `apps/web/tests/components/setup.ts` 接入 CT 测试 setup。
- [x] 创建 `apps/web/src/test/` 目录。
- [x] 创建 `apps/web/src/test/render.tsx`。
- [x] 实现 `renderWithProviders`。
- [x] 从测试公共入口导出 RTL 常用工具和 `userEvent`。
- [x] 保留现有 `placeholder-panel.spec.tsx`，新增 `placeholder-panel-rtl.spec.tsx`。
- [x] 运行 `bun run --cwd apps/web test:ct`。
- [x] 运行 `bun run lint`。
- [x] 运行 `bun run build --filter=web`。
- [x] 运行 `openspec validate web-rtl-test-utils --type change --strict --json`。

## 实现护栏

- 不重做 Playwright E2E 或 CT runner 基础设施。
- 不把 helper 绑定到具体业务页面、API client 或网络 mock。
- 不把 QueryClient 自定义注入接口作为本 change 的稳定公共 API。
- 不让 CT setup 影响 Vitest Node unit tests 或 Playwright E2E tests。
- 不要求所有现有或未来组件一次性迁移到该 helper。
