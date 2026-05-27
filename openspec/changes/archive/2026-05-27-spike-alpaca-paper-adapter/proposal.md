## 背景

issue #158 需要在 issue #157 的 broker simulator test harness V1 完成之后，用一个受控的 Alpaca paper adapter spike 校准真实第三方 paper broker API 与 QuantAgent wallet 外部接入式 contract 之间的差距。本 change 的“完成之后”指 #157 的 OpenSpec artifacts、测试 helper、contract-style 测试和验证说明已经存在，并且后续实现可以直接复用 `BrokerSimulatorHarness`、`BrokerSimulatorExecutionInput.source_key` 与 `WalletService.ingest_paper_execution` 这条入账链路。

#157 解决的是本地可重复性：无网络、无 secret、无真实券商依赖地验证 broker-shaped 输入能驱动 wallet core 的入账、幂等、账本和 Decimal 语义。但本地 simulator 不能暴露真实第三方 API 的字段形态、认证方式、网络失败、错误响应、paper order 状态和 activities/fills 语义。Alpaca 适合作为第一家 paper broker spike，因为它提供 paper trading 环境，paper API domain 使用 `https://paper-api.alpaca.markets`，并通过 `APCA-API-KEY-ID` / `APCA-API-SECRET-KEY` header 认证。

本 change 只定义 Alpaca paper adapter spike 的 OpenSpec 文档和后续实现边界。它不把 Alpaca 接入提升为 Portfolio Wallet Core V1 稳定能力，不修改 `portfolio-wallet-core-v1` stable spec，也不打开 live trading、真实资金操作或正式 broker plugin 能力。

## 改动

- 新增 `alpaca-paper-adapter-spike` 能力，定义 issue #158 的 Alpaca paper-only adapter spike、配置、脱敏、外部 smoke test 和 wallet contract 校准边界。
- 明确本 change 严格依赖 #157 完成；Alpaca adapter 只能消费 #157 已形成的 `BrokerSimulator*` 测试协议、`source_key` 幂等语义和 `WalletService` 受控入账入口，不能反向定义或放宽 wallet core contract。
- 规定第一版实现落在测试 / spike 边界，默认写入边界是 `packages/core/tests/**`；不作为稳定 runtime adapter 导出，不进入 `packages/adapters` 正式 API，也不放入 `plugins/executors` 作为官方 Alpaca executor plugin。
- 规定 Alpaca 连接只能使用 paper base URL `https://paper-api.alpaca.markets`，不得接受 live endpoint 作为默认值、fallback 或 smoke test 目标。
- 规定 credentials 只从环境变量或受控 secret 注入读取；缺少 `QUANTAGENT_ALPACA_PAPER_SMOKE=1`、paper base URL guard 或 paper credentials 任一条件时，外部 smoke test 必须 skip，默认 CI 不依赖网络或 secret。
- 规定 account、positions、orders 的只读 smoke 可以在显式启用后访问 Alpaca paper；paper order submit 只作为额外显式可选 smoke，除满足只读 smoke 的全部条件外，还必须同时满足 `QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE=1`、symbol 白名单、notional / quantity 上限、paper URL guard 和 QuantAgent 生成的 `client_order_id`。
- 规定 fills / activities、错误响应和 execution 入账映射必须可通过 mock transport 或脱敏 recorded response 稳定验证，不依赖真实 paper order 必然成交。
- 规定 adapter 不直接写 wallet 表；任何与 execution / fill 相关的 wallet 入账只能通过 wallet core 受控入口、ledger 和幂等路径完成。

## 能力

### 新增能力

- `alpaca-paper-adapter-spike`: 定义 Alpaca paper broker smoke spike 的 paper-only 接入、配置、脱敏、测试分层、可选 paper order submit 和 wallet contract 校准边界。

### 修改能力

- None.

## 影响

- `openspec/changes/add-broker-simulator-test-harness-v1/**`: 本 change 的前置依赖和 broker-shaped contract 真源。
- `packages/core/tests/**`: 后续实现中 Alpaca spike helper、mock transport、脱敏 recorded response、默认 skip 的外部 smoke test 和 contract-style 测试的默认落位。
- `packages/core/src/quantagent/core/wallet/**`: 后续实现只能通过 wallet core 受控入口消费 execution / fill 映射，不允许 adapter 直接写 wallet 表。
- `openspec/specs/portfolio-wallet-core-v1/spec.md`: 本 change 依赖该 stable spec 的 paper-only、ledger 和幂等边界，但不修改它。
- `docs/design/03-plugin-system-and-registry.md`: 作为长期 plugin / executor 边界参考；本轮不实现 Alpaca official plugin、Registry lifecycle 或真实 executor。
