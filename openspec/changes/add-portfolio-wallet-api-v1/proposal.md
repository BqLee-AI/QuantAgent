## Why

issue #120 已经把 Portfolio Wallet Core V1 的 `packages/core` 领域契约、持久化、入账服务、查询服务和 wallet facts 边界归档为 stable spec，但 issue #134 需要的 FastAPI 只读资源边界仍未落地。继续让前端、调试或集成验证绕过正式 route 直接依赖 core service，会让 DTO、错误映射、脱敏规则和 “only 虚盘，不操作实盘” 语义在 API 层漂移。

本 change 为 issue #134 新建 active OpenSpec，用来定义并交付 `apps/api` 对 Portfolio Wallet Core V1 的受保护、只读、paper-only HTTP 薄封装。当前 PR 不是 OpenSpec-only 评审；它包含该 change artifacts，以及在审核通过后并入的 API runtime、测试与 README 更新。

## What Changes

- 新增 Portfolio Wallet API V1 能力，暴露受保护的只读 wallet account、cash balance、position、ledger entry、paper order 和 paper execution 查询资源。
- 规定 API route 必须通过 API v1 protected registration boundary 注册，使用 `ApiResponse[T]` envelope、显式 OpenAPI tags 和独立 Pydantic DTO。
- 规定 API DTO 从 `WalletService` 返回的 snapshot 映射而来，不直接返回 ORM model、core dataclass、`WalletFacts` 或本地 runtime 细节。
- 规定 API 层只负责鉴权、DTO、响应 envelope、HTTP 错误映射和调用 core service，不实现余额、持仓、账本、入账或风控计算。
- 规定 endpoint、schema、错误文案和测试都必须明确表达 `paper` 虚盘账户能力，不暗示真实 broker action、live sync、真实下单、撤单、改单、换汇或资金划转。
- 规定本轮不开放账户创建、人工调整、paper order 写入、paper execution 写入、wallet facts 前端 endpoint 或 Policy Gate consumer 接线。
- 规定本轮不新增 `packages/contracts` 手写 schema；跨端契约先以 FastAPI/OpenAPI 输出为准。

## Capabilities

### New Capabilities

- `portfolio-wallet-api-v1`: 定义 Portfolio Wallet Core V1 在 `apps/api` 的受保护只读 HTTP 薄封装、DTO/envelope、错误映射、OpenAPI 和 paper-only 非目标边界。

### Modified Capabilities

- None.

## Impact

- `apps/api/src/quantagent/api/schemas/**`: 新增 wallet API response DTO，独立于 ORM model 和 core dataclass。
- `apps/api/src/quantagent/api/routers/v1/**`: 新增 wallet API v1 router，并通过 `register_api_v1_routes` 的 protected registration boundary 注册。
- `apps/api/src/quantagent/api/db.py`: 复用请求级 session / app lifecycle 数据库边界，为 `WalletService` 提供明确注入点。
- `apps/api/src/tests/**`: 补 route runtime、auth protection、DTO/envelope、OpenAPI、Decimal/datetime 和敏感信息不泄露测试。
- `apps/api/README.md`: 记录新增 wallet 只读 API 边界和验证命令。
- `packages/core/src/quantagent/core/wallet/**`: 本 change 只消费已归档 core service / snapshot 契约，不要求改变 core 领域语义。
- `openspec/specs/portfolio-wallet-core-v1/spec.md`: 本 change 依赖该 stable spec，但不修改其已归档 core requirement。
