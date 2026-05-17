# Tasks: API Client 与全局错误治理

## Task Graph

### Blocking Path

- [x] B1. 恢复缺失的 change 到项目当前 OpenSpec 目录
  - Input: issue #8、PR #51 files view、当前仓库 `openspec/` 结构
  - Output: `openspec/changes/api-client-error-governance/` 下的 proposal/spec/tasks
  - Write boundary: `openspec/changes/api-client-error-governance/**`

- [x] B2. 在 `apps/web` 落地基础 API 类型与错误治理
  - Input: issue #8 的 envelope、错误治理、鉴权和 401 需求
  - Output: `types.ts`、`errors.ts`
  - Write boundary: `apps/web/src/shared/api/types.ts`, `apps/web/src/shared/api/errors.ts`

- [x] B3. 实现可复用 API client
  - Input: Axios、401 静默刷新、生命周期取消、请求去重需求
  - Output: `client.ts`、`index.ts`
  - Write boundary: `apps/web/src/shared/api/client.ts`, `apps/web/src/shared/api/index.ts`

- [x] B4. 基于已合入 `main` 的测试基础设施补齐并验证 #8 测试
  - Input: `PR #63` 已合入的单元测试链路、issue #8 验收点
  - Output: 在现有 Vitest runner 上补齐 API client feature-level tests，并完成验证
  - Write boundary: `apps/web/src/shared/api/*.test.ts`

### Parallelizable Work

- [x] P1. 显式声明 `axios` 依赖
  - Can start after: B2
  - Input: `apps/web/package.json`
  - Output: `axios` 被声明为 `apps/web` 直接依赖
  - Write boundary: `apps/web/package.json`

### Review Points

- [x] R1. 确认恢复后的 spec 使用仓库当前 `openspec/` 结构，而不是旧的 `docs/openspec/` 路径。
- [x] R2. 在吸收 `main` 上 `PR #63` 后，确认实现与 spec 一致，并覆盖 envelope、鉴权、401 refresh、请求去重、AbortSignal。

## Verification

- [x] `bun --cwd apps/web run test:unit` 通过
- [x] `bun run lint` 通过
- [x] `bun run build --filter=web` 通过

