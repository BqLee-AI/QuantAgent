# Change: API Client 与全局错误治理

## Source

- GitHub issue: https://github.com/BqLee-AI/QuantAgent/issues/8
- Recovery source: https://github.com/BqLee-AI/QuantAgent/pull/51/files
- State: OPEN

## Why

`apps/web` 目前还没有统一的数据访问层。页面和后续 TanStack Query consumer 缺少可复用的 HTTP client、错误治理、401 会话恢复和取消控制，导致 #8 描述的能力仍未落地。

此前 `PR #51` 已经产出过一版 spec，但文件落在了仓库当前不会消费的 `docs/openspec/...` 路径，而本仓库实际使用的是根目录 `openspec/...`。因此 spec 在主流程中“消失”了，issue 也一直没有完成。

## Problem

- `shared/api` 目录不存在，前端没有统一 `apiClient`。
- 缺少 envelope `code/data/msg` 自动解包与错误转换。
- 401 静默刷新没有统一实现，并发场景也没有共享恢复逻辑。
- 缺少业务错误码注册表和上层 UI 行为约定。
- `PR #51` 的 spec 没有落到项目当前 OpenSpec 结构，后续实现和验证无法持续跟踪。

## Goals

- 在 `apps/web` 落地基于 Axios 的强类型 `apiClient`。
- 支持 `code/data/msg` envelope 自动解包，并保留完整 envelope 访问入口。
- 支持可开关的 Bearer token 注入，默认不启用。
- 支持 401 静默刷新、请求重放和并发 refresh 去重。
- 定义 `ApiError`、`ErrorRegistry` 和全局错误捕获钩子。
- 支持 `AbortSignal` 取消请求，并为重复 GET 请求提供基础去重。
- 将缺失的 spec 恢复到根目录 `openspec/changes/api-client-error-governance/`。

## Non-Goals

- 不实现具体登录页面、toast/modal 组件或用户提示 UI。
- 不定义后端全部业务错误码枚举，只提供前端侧框架和占位。
- 不实现真实 trace id 生成，只保留注入 TODO。
- 不引入 React Query 封装层；本 change 仅提供底层 client。

## Known Context

- `apps/web/src/shared/config/runtime.ts` 已经存在 `authEnabled` runtime 开关。
- `apps/web` 已接入 Vitest Node runner，可直接承接 API client 的单元测试。
- `apps/web/node_modules/axios` 已存在，但 `apps/web/package.json` 之前未显式声明依赖。
- 当前仓库的 spec 约定使用根目录 `openspec/changes/*`，而不是 `docs/openspec/*`。

## What Changes

- 恢复 `api-client-error-governance` change 到根目录 `openspec/changes/`。
- 新增 `apps/web/src/shared/api/` 下的类型、错误治理、client 和导出入口。
- 在 `apps/web/package.json` 显式声明 `axios`。
- 增加 API client 单元测试，覆盖成功、业务错误、401 恢复、并发 refresh 去重、请求去重和 `AbortSignal` 透传。

## Success Criteria

- 开发者调用 `apiClient.get<User>("/me")` 可直接获得 `User`。
- 开发者调用 `apiClient.requestEnvelope<User>("/me")` 可获得完整 `{ code, data, msg }`。
- `authEnabled=true` 时可自动注入 `Authorization: Bearer <token>`。
- 401 响应可触发静默刷新并重放原请求；并发 401 只触发一次 refresh。
- 业务错误被统一转换为 `ApiError`，保留 `code`、`msg`、`request_id`、`trace_id`、`status`。
- `openspec validate api-client-error-governance --type change --strict --json` 通过，且作为本 change 被接受的前置条件。
- `bun --cwd apps/web run test:unit`、`bun run lint`、`bun run build --filter=web` 通过。

## Open Questions

- 后端最终的 error code 枚举仍需补齐到 `ErrorRegistry`。
- 刷新 token 接口的路径与契约仍由后端接口方案决定；当前 client 通过注入 `refreshAccessToken` hook 适配。
- trace header 的生成策略仍待统一。
