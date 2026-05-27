## Why

`add-portfolio-wallet-api-v1` 已经定义并验证了 `apps/api` 的 wallet 只读 HTTP 边界，`spike-alpaca-paper-adapter` 已经在测试 / spike 边界验证了 Alpaca paper 只读连接与字段映射。当前缺口是：还没有一组受控验证能证明“真实 Alpaca paper 数据经过 wallet ingestion 后，可以通过既有 `apps/api` wallet endpoints 被读出”。

本 change 用于补齐这条跨边界验证链路，但不把 Alpaca 接入产品化，不新增对外 Alpaca API，也不改变 Portfolio Wallet Core V1 的稳定能力范围。

## What Changes

- 新增一组 Alpaca paper -> wallet ingestion -> `apps/api` wallet read endpoints 的端到端验证能力；该能力是测试 / 验证能力，不是运行时同步能力。
- 复用 `spike-alpaca-paper-adapter` 的 paper-only URL guard、环境变量、credentials 注入、脱敏和默认 skip 约束。
- 复用 `add-broker-simulator-test-harness-v1` 已形成的 broker-shaped execution / `source_key` / `WalletService.ingest_paper_execution` contract。
- 复用 `add-portfolio-wallet-api-v1` 的既有 wallet 只读 endpoints，不新增 Alpaca 专用 route，不改变现有 API schema。
- 增加默认无网络、无 secret、无 `.env` 的本地集成测试；真实 Alpaca paper 端到端 smoke 只在显式开关和 credentials 同时存在时运行。
- 明确真实外部 smoke 只能读取 account、positions、orders；本地 wallet 中使用脱敏派生 identifier，不持久化或断言真实 account id / order id；默认不提交 paper order。
- 明确本 change 不证明 live trading、正式 broker adapter、官方 Alpaca plugin、reconciliation 或 broker snapshot sync 可用。

## Capabilities

### New Capabilities

- `alpaca-wallet-api-e2e-validation`: 定义 Alpaca paper 数据进入 wallet ingestion 后，再通过既有 `apps/api` wallet 只读 endpoints 读出的受控端到端验证能力。

### Modified Capabilities

- None.

## Impact

- `openspec/changes/spike-alpaca-paper-adapter/**`: 作为 Alpaca paper-only 配置、脱敏、URL guard 和 smoke 分层的前置真源。
- `openspec/changes/add-broker-simulator-test-harness-v1/**`: 作为 broker-shaped execution、幂等 `source_key` 和 wallet ingestion 路径的前置真源。
- `openspec/changes/add-portfolio-wallet-api-v1/**`: 作为 `apps/api` wallet 只读 endpoint、DTO、envelope 和错误映射的前置真源。
- `packages/core/tests/**`: 仅在现有 helper 无法被 `apps/api` 测试复用时，才允许补充测试 helper；不得新增生产导出。
- `apps/api/src/tests/**`: 新增默认离线的 API 集成验证与可选外部 smoke 验证，优先作为主要实现落位。
- `apps/api/src/quantagent/api/routers/v1/**`: 本 change 默认不修改 route；若实现发现必须修改 route，需先回到 OpenSpec 更新设计并说明原因。
