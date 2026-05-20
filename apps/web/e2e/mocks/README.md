# Route Mock 扩展点

本目录存放由 issue `#55` 引入的共享网络 mock 工具。

## 边界

- `mockEnvelope.ts`：纯数据 envelope 构造工具，不依赖 Playwright
- `route-mock.ts`：Playwright `page.route` 适配器，复用 `mockEnvelope.ts`
- 页面级浏览器测试保持在 `../`

## 消费方

- `apps/web/e2e/**`：浏览器测试应直接复用这两个 helper
- `apps/web/tests/**` 和 `apps/web/src/**/*.test.ts`：当需要相同的响应 envelope 语义但不需要浏览器运行时，可以导入 `mockEnvelope.ts`

## 范围

- HTTP error 指服务端返回带有 HTTP status 和响应体的响应
- network failure 指请求层失败，例如 `route.abort(...)`
- 401 recover helpers 仅预留场景入口；不实现真实的 refresh endpoint、cookie 行为或请求重放
