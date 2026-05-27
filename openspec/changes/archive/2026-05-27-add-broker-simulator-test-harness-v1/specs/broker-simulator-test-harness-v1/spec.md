## ADDED Requirements

### Requirement: Broker Simulator Test Harness V1 以 wallet core 外部接入式验证为目标

QuantAgent SHALL define Broker Simulator Test Harness V1 as a local, repeatable, broker-shaped validation layer for Portfolio Wallet Core V1.

#### Scenario: Harness 验证外部输入驱动 wallet core
- **WHEN** QuantAgent tests Portfolio Wallet Core V1 after issue #120 and issue #134
- **THEN** the tests exercise wallet behavior through broker-shaped external inputs
- **AND** they do not rely only on internal service or repository setup as the proof of correctness

#### Scenario: Harness 不连接真实券商
- **WHEN** Broker Simulator Test Harness V1 is executed
- **THEN** it does not call real broker APIs
- **AND** it does not require external network access
- **AND** it does not load real broker credentials, API keys, OAuth tokens or production account configuration

#### Scenario: Harness 不打开真实执行能力
- **WHEN** documentation, tests or fixtures describe the harness
- **THEN** they describe it as a broker simulator or paper harness
- **AND** they do not imply live trading, real order placement, real cancellation, real modification, real FX transfer or real cash transfer support

### Requirement: 第一版 harness 落在 core 测试边界

Broker Simulator Test Harness V1 SHALL be implemented first as a `packages/core` test asset rather than a runtime plugin.

#### Scenario: 第一版实现位置
- **WHEN** the first version of the harness is implemented
- **THEN** its main fixtures, helpers and contract-style tests live under `packages/core/tests/**`
- **AND** it may keep adapter-shaped seams for future reuse
- **AND** it is not required to be installed from `plugins/` or `runtime/plugins/`
- **AND** it does not require production changes under `apps/api`, `plugins/`, `runtime/plugins/` or `packages/plugin-sdk` unless exposing an existing wallet service seam is strictly necessary

#### Scenario: 第一版不要求 plugin runtime 集成
- **WHEN** the first version is reviewed
- **THEN** it is acceptable that no `plugin.yaml` discovery, Registry scan, runtime install or plugin lifecycle execution is involved
- **AND** future plugin runtime integration remains a separate capability

### Requirement: Harness 输入必须保留 broker-shaped 语义

Broker Simulator Test Harness V1 SHALL define minimal broker-shaped inputs for wallet-related external data.

#### Scenario: Harness 表达最小外部输入
- **WHEN** the harness defines its test protocol or fixtures
- **THEN** it can express broker account, cash balance, position, paper order, paper execution and broker error inputs
- **AND** those inputs are shaped as external adapter data rather than internal ORM or snapshot rows
- **AND** broker account, cash balance and position shapes may be used as fixture context or expected-state descriptors without requiring a new production snapshot-sync API in V1

#### Scenario: 测试不直接以内部 snapshot 作为外部输入
- **WHEN** contract-style tests prepare simulator data
- **THEN** they do not treat core ORM models or internal wallet snapshots as the canonical broker input shape
- **AND** they map broker-shaped test input into wallet core through controlled seams

### Requirement: 外部 execution 必须具备稳定幂等来源

Broker Simulator Test Harness V1 SHALL require account-scoped stable external execution identity for duplicate-ingestion protection.

#### Scenario: 外部 execution 携带稳定 source key
- **WHEN** the harness submits a broker execution into wallet core
- **THEN** the input includes an account-scoped stable external execution identifier or source key
- **AND** the tests use that identity as the duplicate-ingestion reference
- **AND** the identity is mapped into the current wallet ingestion seam as `idempotency_key` or an equivalent service-level field

#### Scenario: 重复提交同一 execution 不重复入账
- **WHEN** the same broker execution or the same external source key is submitted more than once
- **THEN** wallet core does not duplicate cash updates
- **AND** it does not duplicate position updates
- **AND** it does not duplicate paper execution records
- **AND** it does not duplicate ledger entries

### Requirement: Harness 只通过 wallet core 受控入口驱动状态

Broker Simulator Test Harness V1 SHALL verify the wallet ingestion path without bypassing core rules.

#### Scenario: Harness 使用 service-level 入口
- **WHEN** the harness triggers wallet state transitions
- **THEN** it uses `WalletService` public commands and queries or a service-level helper that applies the same domain rules
- **AND** repository methods or ORM models are not used as the primary harness entrypoint

#### Scenario: Simulator 不直接写 wallet 表
- **WHEN** the harness drives wallet state changes
- **THEN** it uses wallet core controlled entry points
- **AND** it does not directly insert or mutate wallet database tables to fabricate the final result

#### Scenario: Simulator 不绕过 ledger 和 core service
- **WHEN** an execution, rejection or fee effect is tested
- **THEN** the resulting cash, position, paper execution and ledger facts come from wallet core behavior
- **AND** the harness does not bypass ledger history or replace it with fixture-only snapshot edits

#### Scenario: Simulator 不进入 API route
- **WHEN** Broker Simulator Test Harness V1 is implemented
- **THEN** no simulator ingestion or adapter mapping logic is added to FastAPI routes
- **AND** API routes remain outside the first-version harness implementation boundary

### Requirement: 第一版必须覆盖关键 broker 场景

Broker Simulator Test Harness V1 SHALL cover the minimum scenarios needed to validate wallet ingestion semantics.

#### Scenario: Full fill execution 入账
- **WHEN** the harness submits a valid full fill broker execution
- **THEN** wallet core updates the relevant cash balance, position snapshot, paper execution record and ledger entries consistently

#### Scenario: Reject 或余额不足不制造错误入账
- **WHEN** the harness simulates a broker rejection or an insufficient-cash condition
- **THEN** wallet core does not produce an invalid successful execution effect
- **AND** the tests verify either a controlled error path or a broker-side no-op ingestion result
- **AND** V1 does not require wallet core itself to implement real-broker-style pre-trade cash checks solely for this harness

#### Scenario: Fee 与多币种字段被验证
- **WHEN** the harness simulates broker execution data with fee and currency fields
- **THEN** the tests verify fee handling and multi-currency field mapping
- **AND** they do not collapse all values into a single float-based balance assertion

#### Scenario: Decimal 语义被固定
- **WHEN** the harness validates amount, quantity, price, fee or FX-related fields
- **THEN** the assertions preserve decimal or fixed-point semantics
- **AND** binary float behavior is not used as the canonical wallet calculation proof

### Requirement: Harness 为后续真实 paper adapter 提供 contract-style 测试雏形

Broker Simulator Test Harness V1 SHALL prepare a reusable contract-style verification pattern for future paper broker adapters.

#### Scenario: Contract-style 测试可复用
- **WHEN** a future real paper broker adapter is introduced
- **THEN** the project can reuse the harness scenarios or helper structure to verify wallet ingestion behavior
- **AND** the adapter does not need to redefine wallet duplicate-ingestion and ledger-consistency expectations from scratch
- **AND** the reusable test entrypoint remains focused on broker-shaped fixture mapping and wallet-ingestion assertions rather than defining a permanent production adapter SDK

#### Scenario: 第一版不固化稳定 plugin SDK
- **WHEN** the first version of the harness is completed
- **THEN** it is acceptable that the reusable contract exists as tests or helpers rather than a stable public SDK
- **AND** formal adapter SDK or plugin SDK design remains a separate follow-up capability
