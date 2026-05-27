# 实现 PR 说明草稿

## 依据

- issue #157
- stable spec `openspec/specs/portfolio-wallet-core-v1/spec.md`

## 本次实现

- 在 `packages/core/tests/` 新增 broker simulator / paper harness 测试 helper，固定 broker-shaped account、cash、position context、order、execution 和 broker error 输入。
- 明确 `source_key` 逐字映射到 `WalletService.ingest_paper_execution()` 的 `RecordPaperExecutionCommand.idempotency_key`，用于账户范围内重复 execution 幂等。
- 新增 contract-style harness tests，覆盖 full fill、duplicate execution、broker reject no-op、insufficient cash、fee、多币种字段和 Decimal 语义。
- 明确 partial fill、plugin runtime 集成、真实 broker adapter 与 broker snapshot sync 仍未进入本轮。

## 已验证

- full fill execution 在同一 wallet ingestion 链路内保持 cash、position、paper execution 和 append-only ledger 一致
- duplicate execution 不会重复扣现金、重复加持仓或重复追加 ledger
- reject 使用 broker-side no-op 表达；insufficient cash 使用 wallet core 受控错误路径表达，且不会留下部分状态
- fee 与多币种字段保持 Decimal / 定点语义
- harness 可在无网络、无真实账户、无真实密钥环境下运行

## 非目标

- live trading
- 真实 broker adapter
- broker snapshot sync / reconciliation
- plugin runtime 集成
- partial fill 完整订单生命周期
