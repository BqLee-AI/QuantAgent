# alpaca-paper-adapter-spike Specification

## Purpose
TBD - created by archiving change spike-alpaca-paper-adapter. Update Purpose after archive.
## Requirements
### Requirement: Alpaca Paper Adapter Spike 依赖 broker simulator contract

QuantAgent SHALL define Alpaca Paper Adapter Spike as a follow-up validation layer that consumes the broker-shaped contract semantics from issue #157.

#### Scenario: #157 完成后再实施 Alpaca spike
- **WHEN** Alpaca Paper Adapter Spike implementation begins
- **THEN** issue #157 `add-broker-simulator-test-harness-v1` has completed its OpenSpec and implementation work
- **AND** `BrokerSimulatorHarness`, `BrokerSimulatorFixture`, `BrokerSimulatorOrderInput`, `BrokerSimulatorExecutionInput.source_key`, `BrokerSimulatorErrorInput` and the wallet ingestion path through `WalletService.ingest_paper_execution` are available as the contract source
- **AND** the spike reads those contract assets before implementing Alpaca mapping

#### Scenario: Alpaca 不反向定义 wallet contract
- **WHEN** Alpaca paper fields do not match the existing broker simulator contract
- **THEN** the spike records the mismatch as a contract gap or follow-up decision
- **AND** it does not silently expand Portfolio Wallet Core V1 or weaken broker simulator expectations to fit Alpaca

### Requirement: Alpaca spike 保持 paper-only 边界

QuantAgent SHALL restrict Alpaca Paper Adapter Spike to Alpaca paper trading endpoints and prevent live trading exposure.

#### Scenario: Paper base URL 被硬校验
- **WHEN** external Alpaca smoke tests or adapter helpers construct an Alpaca request
- **THEN** the base URL is verified as `https://paper-api.alpaca.markets`
- **AND** live trading endpoints are not accepted as defaults, fallbacks or alternate smoke targets
- **AND** any configured base URL with a different scheme, host or path causes the smoke test to skip or fail fast before sending a request

#### Scenario: Spike 不打开 live trading 能力
- **WHEN** the Alpaca spike is implemented or documented
- **THEN** it does not expose live order placement, live cancellation, live replacement, live FX transfer, real cash transfer or production broker execution capability
- **AND** successful Alpaca paper smoke tests are not described as proof that live trading is safe or available

#### Scenario: Spike 不扩展 Wallet V1 资产类别
- **WHEN** Alpaca paper responses contain margin, options, crypto, short selling or complex asset-class fields
- **THEN** those fields are ignored or recorded as out of scope for this spike
- **AND** Portfolio Wallet Core V1 remains limited to its existing paper wallet and stock-like spot abstraction unless a separate OpenSpec change expands it

### Requirement: Credentials 与外部 smoke 默认安全关闭

QuantAgent SHALL keep Alpaca credentials and network-dependent tests out of default validation.

#### Scenario: Credentials 缺失时 smoke skip
- **WHEN** Alpaca paper credentials or the explicit smoke enable flag are missing
- **THEN** external Alpaca smoke tests are skipped
- **AND** default CI and local Python tests can pass without network access, Alpaca account credentials or a local `.env`

#### Scenario: Authentication headers 来自受控注入
- **WHEN** Alpaca paper requests are made
- **THEN** credentials are read from `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` environment variables or controlled CI secrets
- **AND** the request uses `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY` headers
- **AND** the repository does not commit real API keys, secrets, account ids, order ids or full raw response fixtures

#### Scenario: Smoke 开关分层
- **WHEN** external smoke tests are evaluated
- **THEN** read-only smoke requires `QUANTAGENT_ALPACA_PAPER_SMOKE=1`
- **AND** order-submit smoke additionally requires `QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE=1`
- **AND** the order-submit flag alone is insufficient to run smoke tests if the read-only smoke flag or credentials are missing

#### Scenario: Secret 不进入日志或断言
- **WHEN** Alpaca configuration, request failure, response failure or smoke skip reason is logged or asserted
- **THEN** API keys, secret keys, account ids, order ids, client order ids and local secret paths are redacted or omitted
- **AND** raw third-party error bodies are not persisted verbatim if they may contain sensitive identifiers

### Requirement: Alpaca paper 数据映射到 broker-shaped contract

QuantAgent SHALL map Alpaca paper account, position, order and activity data into the broker-shaped contract used by the wallet harness.

#### Scenario: 只读 smoke 覆盖账户和仓位订单查询
- **WHEN** external Alpaca read-only smoke is explicitly enabled
- **THEN** it queries paper account, positions and orders
- **AND** it verifies their minimum field mapping into the broker-shaped contract
- **AND** it does not write wallet state solely because the read-only smoke ran

#### Scenario: Cash 与 buying power 映射被校准
- **WHEN** Alpaca paper account data includes cash or buying power values
- **THEN** `cash` may be mapped into broker-shaped cash context for testing
- **AND** `buying_power` is treated as broker account context or risk evidence rather than wallet ledger cash truth
- **AND** the mapping preserves decimal or fixed-point semantics rather than using binary float as canonical proof

#### Scenario: Order 状态映射不替代 execution fact
- **WHEN** Alpaca paper order responses are mapped
- **THEN** order status is represented as broker order state
- **AND** order status alone is not treated as the wallet execution fact
- **AND** execution or fill ingestion remains based on activities, fills or equivalent execution-shaped data

### Requirement: Fill 与错误路径可离线验证

QuantAgent SHALL validate Alpaca fill/activity mapping and broker error mapping without requiring live network access.

#### Scenario: Fill 映射使用 mock 或脱敏 response
- **WHEN** the spike validates Alpaca account activity or fill data
- **THEN** it uses mock transport or redacted recorded response fixtures for deterministic tests
- **AND** those tests run without Alpaca credentials or network access
- **AND** the fixture contains no real secret, account id, order id or full raw third-party response
- **AND** retained identifiers use stable placeholders such as `acct_redacted`, `order_redacted_1` or `activity_redacted_1`

#### Scenario: Fill 入账使用稳定 source key
- **WHEN** an Alpaca fill or activity is mapped into wallet execution ingestion
- **THEN** the mapped broker execution includes an account-scoped stable external source key
- **AND** the source key maps to the wallet idempotency seam from #157 or an equivalent wallet service-level field
- **AND** replaying the same fill or activity does not duplicate cash, position, paper execution or ledger effects

#### Scenario: Broker 错误被脱敏并分类
- **WHEN** Alpaca responds with authentication failure, invalid symbol, insufficient buying power, timeout or external unavailable conditions
- **THEN** the spike maps the condition into a controlled broker error category
- **AND** the mapped error message omits secrets, full identifiers, raw headers and full third-party response bodies

### Requirement: Paper order submit 是额外显式可选 smoke

QuantAgent SHALL make Alpaca paper order submission optional, bounded and separate from default smoke validation.

#### Scenario: Order submit 需要额外开关
- **WHEN** Alpaca paper order submit smoke is considered
- **THEN** it runs only when an order-specific explicit enable flag is present
- **AND** the generic external smoke flag alone is insufficient to submit an order

#### Scenario: Order submit 受白名单和上限约束
- **WHEN** order submit smoke sends an Alpaca paper order
- **THEN** the symbol is included in the configured smoke-test whitelist
- **AND** notional is no greater than `5 USD` when a notional order is used
- **AND** quantity is no greater than `1` when a quantity order is used
- **AND** unsupported order shapes are skipped rather than allowed to increase those upper bounds
- **AND** the request uses the verified paper base URL
- **AND** the request includes a QuantAgent-generated `client_order_id`

#### Scenario: Order submit smoke 不要求真实成交
- **WHEN** order submit smoke completes
- **THEN** the test may verify order submission and query status
- **AND** it does not require the paper order to fill
- **AND** cancel, replace and multi-order lifecycle behavior remain out of scope for this spike

### Requirement: Adapter 不绕过 wallet core 受控入口

QuantAgent SHALL prevent Alpaca adapter spike code from becoming a private wallet state writer.

#### Scenario: Adapter 不直接写 wallet 表
- **WHEN** Alpaca fill or execution data is ingested into wallet behavior
- **THEN** the adapter maps it to `BrokerSimulatorExecutionInput` or an equivalent broker-shaped execution accepted by the #157 contract
- **AND** the adapter uses wallet core controlled service-level entry points
- **AND** it does not directly insert or update wallet ORM tables, cash snapshots, position snapshots, paper execution rows or ledger entries

#### Scenario: Adapter 不进入 API route 或 plugin runtime
- **WHEN** the first Alpaca spike is implemented
- **THEN** Alpaca-specific mapping and smoke code stay in the test / spike boundary
- **AND** FastAPI routes, Registry lifecycle and official plugin runtime do not become responsible for Alpaca spike behavior

#### Scenario: 正式 adapter 或 plugin 需要后续 change
- **WHEN** the project wants to promote Alpaca support into `packages/adapters`, `packages/plugin-sdk` or `plugins/executors`
- **THEN** it creates a separate issue and OpenSpec change
- **AND** that follow-up defines stable package boundaries, plugin manifest, configuration schema, lifecycle and validation requirements

