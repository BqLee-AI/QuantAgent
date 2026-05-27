## Status

- [x] 本 change 的 OpenSpec 审核门禁已完成；实现按审核后的 change 继续推进。
- [x] 当前实现范围保持在测试 / 验证能力内，没有新增 Alpaca API route、runtime adapter 或官方 plugin。
- [x] 外部 Alpaca paper E2E smoke 维持为可选补充验证；离线 E2E 仍是本 change 的必跑验收。

## Graph Overview

关键路径：`R0 -> B0 -> B1 -> P1/P2 -> M0 -> V0 -> PR0`。

`B1` 完成前保持单人串行，因为测试 harness、脱敏策略和 smoke gate 是所有后续任务共享的基础。`B1` 后，离线 E2E（`P1`）和外部 smoke gate（`P2`）可以并行，但需要在 `M0` 合并验证结论。

## Blocking Serial Path

- [x] B0: 确认前置资产。输入：`add-portfolio-wallet-api-v1`、`add-broker-simulator-test-harness-v1`、`spike-alpaca-paper-adapter` 的 proposal/design/spec/tasks 和当前实现文件。输出：实现 notes 明确复用哪些 route、DTO、helper、guard、mapper 和 wallet ingestion contract。写入边界：实现 notes 或 PR 说明；不改代码。依赖：`R0`。并行资格：否，后续任务都依赖这些真源。验证：能列出 `/api/v1/wallet/**` 读 endpoint、`WalletService.ingest_paper_execution`、`BrokerSimulatorExecutionInput.source_key` 和 Alpaca paper URL guard 的复用点。
- [x] B1: 固化 E2E 测试契约。输入：`B0`、本 change design/spec。输出：离线 fixture 命名、脱敏 identifier 规则、`QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE` gate、skip reason、API readback 断言范围。写入边界：`apps/api/src/tests/**`，必要时 `packages/core/tests/**` 测试 helper。依赖：`B0`。并行资格：否，`P1` 和 `P2` 都消费同一测试契约。验证：新增或更新的测试能证明无 credentials 时默认 skip / 默认离线。

## Parallel Work After B1

- [x] P1: 实现离线 E2E。输入：`B1`、脱敏 Alpaca-shaped fixture、wallet API route 测试模式。输出：默认运行的 `apps/api` 离线 E2E 测试，覆盖 account、cash、position、ledger、paper order、paper execution 通过 API 读出。写入边界：`apps/api/src/tests/**`；若必须补 helper，仅限 `packages/core/tests/**`。依赖：`B1`。并行资格：是，可与 `P2` 并行，因为主要写入 API 测试文件。验证：无网络、无 credentials、无 `.env` 时通过。
- [x] P2: 实现外部 E2E smoke gate。输入：`B1`、Alpaca paper URL guard、credentials 读取和脱敏 helper。输出：默认 skip 的外部 E2E smoke，只有 `QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE=1`、`QUANTAGENT_ALPACA_PAPER_SMOKE=1`、paper credentials 和 paper URL guard 同时满足时运行。写入边界：`apps/api/src/tests/**`，必要时 `packages/core/tests/**` 测试 helper。依赖：`B1`。并行资格：是，可与 `P1` 并行，但不得修改同一个测试文件。验证：缺少任一条件时 skip reason 不含 secret 或真实 identifier。

## Merge / Integration Nodes

- [x] M0: 合并 E2E 验证结论。输入：`P1`、`P2`。输出：一个明确结论：离线 E2E 是否证明 Alpaca-shaped 数据经 wallet ingestion 后能由 API 读出；外部 smoke 是否只作为可选补充；是否存在字段 mapping gap。写入边界：测试 README、实现 notes 或 PR 说明。依赖：`P1`、`P2`。验证：审阅者能区分离线必跑验收与外部可选 smoke。
- [x] M1: 敏感信息检查。输入：所有新增测试、fixture、README 和 PR 说明。输出：确认没有真实 API key、secret、account id、order id、client order id 或完整第三方响应进入仓库。写入边界：必要时修正测试和文档。依赖：`M0`。验证：使用 `rg` 检查明显 secret / identifier 模式，并人工确认 fixture 只含占位值。

## Review Checkpoints

- [x] R0: OpenSpec-only review gate。输入：本 change proposal/design/spec/tasks。输出：OpenSpec PR 被批准或维护者明确评论“没问题”。写入边界：`openspec/changes/add-alpaca-wallet-api-e2e-validation/**`。依赖：无。验证：`openspec validate add-alpaca-wallet-api-e2e-validation --type change --strict --json` 通过。
- [x] R1: 设计漂移 checkpoint。输入：实现中的 route、helper、smoke gate 和脱敏策略。输出：确认实现没有新增 Alpaca API route、runtime adapter、plugin 或 live endpoint；若发现必须新增生产代码，暂停并更新 OpenSpec。依赖：`B1`、`P1`、`P2`。验证：代码 diff 不包含 `apps/api` Alpaca route 或 `packages/core/src/**` Alpaca runtime 导出。

## Validation Nodes

- [x] V0: OpenSpec 严格校验。命令：`openspec validate add-alpaca-wallet-api-e2e-validation --type change --strict --json`。依赖：任意 OpenSpec artifact 编辑。预期：valid true，0 issues。
- [x] V1: 现有 API 回归。命令：`uv run python -m unittest apps/api/src/tests/test_app.py`。依赖：`P1`、`P2`。预期：现有 wallet API route 测试仍通过。
- [x] V2: 新增离线 E2E 测试。命令：使用实现时新增的窄 unittest pattern。依赖：`P1`、`M0`。预期：无网络、无 credentials、无 `.env` 时通过。
- [x] V3: 外部 Alpaca paper E2E smoke。命令：由测试 README 记录，必须包含 `QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE=1`、`QUANTAGENT_ALPACA_PAPER_SMOKE=1` 和 paper credentials。依赖：`P2`、`M0`。预期：PR 说明记录是否运行、是否访问 Alpaca paper、是否提交 paper order；未运行时说明原因。
- [x] V4: 敏感信息验证。命令：使用 `rg` 和人工检查确认新增文件不含真实 secret、account id、order id、client order id 或完整第三方响应。依赖：`M1`。预期：仅存在占位 identifier 和环境变量名。

## Multi-Agent Plan

- [ ] 单人优先完成 `B0` 和 `B1`，因为测试契约、脱敏规则和 smoke gate 需要统一。
- [ ] `B1` 后可以把 `P1` 与 `P2` 拆给不同实现者，但必须保证写入文件不重叠，并由一个 owner 负责 `M0` 合并结论。
- [ ] 不并行处理任何新增 runtime route、adapter 或 plugin 工作；如果实现者认为需要这些能力，必须暂停并回到 OpenSpec 评审。

## PR Readiness

- [x] PR0: 实现 PR 说明链接本 change，写明前置依赖状态、改动摘要、离线 E2E 结果、外部 E2E smoke 结果或未运行原因、是否提交 paper order、敏感信息检查结果，并明确 live trading、官方 Alpaca plugin、runtime adapter promotion 和 broker reconciliation 不在范围内。
