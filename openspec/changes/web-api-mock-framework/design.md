## Context

issue #55 只定义前端网络 mock 测试底座。当前仓库已经具备 `apps/web/e2e/**`、`apps/web/tests/**`、`apps/web/src/**/*.test.ts` 三类测试边界，并在 `apps/web/e2e/mocks/README.md` 预留了 Playwright route mock 扩展位。本 change 需要在不扩大范围的前提下，把纯数据 envelope 构造层和 Playwright route 拦截层的职责、目录和 401 边界收敛清楚。

## Goals / Non-Goals

**Goals:**

- 建立前端测试使用的统一网络 mock 资产边界和命名约定。
- 把 `mockEnvelope.ts` 收敛为纯数据 envelope 构造层，把 `route-mock.ts` 收敛为 Playwright route 拦截层。
- 明确 HTTP error 与 network failure 的测试语义差异。
- 为 401 recover 预留测试表达能力，但不固化真实 refresh/cookie/重放实现。
- 提供最小浏览器测试证明。

**Non-Goals:**

- 不实现 `apiClient`、Axios instance、response interceptor 或真实 refresh 流程。
- 不引入 MSW 作为本轮方案。
- 不设计完整业务 fixtures 或覆盖所有资源 endpoint。
- 不把 mock helper 暴露为运行时代码的一部分。

## Decisions

### 1. 采用两层 mock 结构

`mockEnvelope.ts` 作为纯数据构造层，必须不依赖 Playwright，供后续 Vitest Node 单测、API Client interceptor 测试和浏览器 route mock 共用。`route-mock.ts` 只负责把这些构造函数接入 `page.route`。

替代方案是只提供 Playwright helper，并在 Node 单测中继续手写 envelope。该方案会让单测和浏览器测试继续维护两套响应结构，因此不采用。

### 2. 目录边界对齐现有 `apps/web` 测试体系

网络 mock 资产必须位于 `apps/web` 测试体系内，并优先对齐现有 `apps/web/e2e/mocks/README.md` 预留的浏览器 mock 扩展位。浏览器 route 拦截层以 `apps/web/e2e/mocks/**` 为首选落位；纯数据 envelope 构造层也应保持在测试目录边界内，使 `apps/web/e2e/**`、`apps/web/tests/**` 和 `apps/web/src/**/*.test.ts` 能复用同一套工具。

替代方案是把纯数据层放入运行时代码目录，例如 `src/shared`。该方案会模糊测试资产与生产代码边界，因此不采用。

### 3. `route-mock.ts` 必须复用 `mockEnvelope.ts`

`route-mock.ts` 不能维护第二套响应格式。所有成功响应、业务错误和带响应体的 HTTP error 都必须复用 `mockEnvelope.ts` 的构造结果；只有请求层失败或 `route.abort` 一类场景才属于 network failure。

替代方案是让 `route-mock.ts` 直接内联 `route.fulfill()` 的 JSON 响应。该方案会让浏览器测试与单测再次分叉，因此不采用。

### 4. HTTP error 与 network failure 分开建模

HTTP error 指服务端返回了明确的 HTTP status 和响应体；network failure 指请求层失败、连接中断或 `route.abort` 一类没有正常 HTTP 响应体的场景。两者必须在 helper 命名和测试语义上分开，避免测试把“服务端错误响应”和“请求未到达服务端”混为一类。

替代方案是统一用 `status >= 400` 表达所有失败。该方案无法覆盖请求层失败与 route abort 场景，因此不采用。

### 5. 401 recover 只预留场景入口

401 unauthorized 与 recover 相关 helper 只用于表达测试意图，例如“首次请求返回 401”“recover 成功或失败”“并发 401 共享 recover 入口”。本 change 不固定 refresh endpoint、cookie 行为或最终请求重放实现。

替代方案是直接把 refresh 接口路径、cookie 依赖和重放时序写入 helper。该方案会越过 issue 55 的范围，因此不采用。

## Risks / Trade-offs

- [Risk] 测试资产散落在多个目录，后续实现者可能不清楚 mock 工具应放在哪里。
  → Mitigation: 明确 `apps/web/e2e/mocks/**` 是浏览器 route mock 的首选落位，并要求其他测试层只作为消费方复用。

- [Risk] 如果 `route-mock.ts` 直接拼接响应 JSON，浏览器测试和单测会再次分叉。
  → Mitigation: 在 spec 中明确 `route-mock.ts` 必须复用 `mockEnvelope.ts`，禁止维护第二套响应格式。

- [Risk] HTTP error 与 network failure 混淆会让测试覆盖失真。
  → Mitigation: 在 helper 命名和 spec scenario 中明确两类失败的语义差异。

- [Risk] 401 recover 范围被误扩展为真实 refresh/cookie 流程。
  → Mitigation: tasks 和 spec 只要求预留 helper 边界与场景入口，不要求实现完整 recover。
