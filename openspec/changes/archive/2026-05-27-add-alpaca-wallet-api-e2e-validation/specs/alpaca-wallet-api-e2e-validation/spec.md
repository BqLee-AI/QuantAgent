## ADDED Requirements

### Requirement: Alpaca Wallet API 端到端验证保持测试边界

QuantAgent SHALL 提供一条受控验证路径，用来证明 Alpaca paper 形态的数据可以进入本地 wallet service，并通过既有 wallet API route 读出，同时不得把 Alpaca 提升为 runtime adapter 能力。

#### Scenario: 验证不新增 Alpaca API route
- **WHEN** 实现 Alpaca Wallet API E2E validation
- **THEN** 不新增公开的 Alpaca 专用 FastAPI route
- **AND** 该验证只使用既有 `/api/v1/wallet/**` 只读 endpoint 作为 API 暴露面

#### Scenario: 验证不改变现有 wallet API contract
- **WHEN** 验证读取 wallet account、cash balances、positions、ledger entries、paper orders 或 paper executions
- **THEN** 它使用既有 wallet API DTO、envelope 和错误映射
- **AND** 它不改变 route path、响应 schema 名称或 paper-only 语义

### Requirement: 离线端到端验证默认可重复

QuantAgent SHALL 使用确定性测试验证 Alpaca-shaped 数据进入 wallet 后再由 API 读出的链路，并且默认不需要网络、credentials 或本地 `.env`。

#### Scenario: 离线测试 seed wallet 后通过 API 读出
- **WHEN** 运行离线 E2E validation
- **THEN** 它从 Alpaca-shaped account、order 和 fill fixture 创建本地 wallet 状态
- **AND** 它通过 `WalletService.ingest_paper_execution` 或 broker simulator contract 路径写入 execution-shaped 数据
- **AND** 它通过既有 `/api/v1/wallet/**` endpoint 读取结果状态
- **AND** API 响应与预期 account、cash、position、order、execution 和 ledger 影响一致

#### Scenario: 离线测试不依赖真实 broker
- **WHEN** 执行默认 unit 或 integration tests
- **THEN** 它们不访问 Alpaca paper
- **AND** 它们在没有 `APCA_API_KEY_ID`、`APCA_API_SECRET_KEY`、`QUANTAGENT_ALPACA_PAPER_SMOKE` 或 `QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE` 时仍可通过

### Requirement: 外部 E2E smoke 显式启用且 paper-only

QuantAgent SHALL 默认关闭真实 Alpaca paper E2E smoke，并且在访问 Alpaca 前要求显式 paper-only 配置。

#### Scenario: 外部 E2E smoke 缺少开关时 skip
- **WHEN** 缺少 E2E smoke flag
- **THEN** 外部 Alpaca Wallet API E2E smoke 被 skip
- **AND** skip 原因不包含 API key、secret key、account id 或本地 secret 路径

#### Scenario: 外部 E2E smoke 只接受 paper endpoint
- **WHEN** 外部 E2E smoke 构造 Alpaca request
- **THEN** base URL 被校验为 `https://paper-api.alpaca.markets`
- **AND** 任何 live endpoint、非 https URL、URL path、query、fragment、auth 或 port 都会在发送请求前导致 smoke skip 或 fail

#### Scenario: 外部 E2E smoke 只读真实 Alpaca paper
- **WHEN** 外部 E2E smoke 被启用
- **THEN** 它可以读取 Alpaca paper account、positions 和 orders
- **AND** 它不提交、取消或修改订单
- **AND** 它在验证说明中记录是否实际访问 Alpaca paper

#### Scenario: 外部 E2E smoke 使用脱敏本地输入
- **WHEN** 外部 E2E smoke 将真实 Alpaca paper 响应用于本地 wallet 验证
- **THEN** 它只在内存中读取真实响应
- **AND** 它写入本地 wallet 的 account id、order id、client order id 和 source key 使用脱敏派生值或稳定占位值
- **AND** 它不把真实 broker identifier 或完整第三方响应写入本地数据库、fixture、日志或断言

### Requirement: Broker 数据进入 wallet 后通过 API 读出

QuantAgent SHALL 证明从 Alpaca paper 派生的 broker-shaped 数据可以表达为本地 wallet 状态，并通过 `apps/api` wallet route 被观察到。

#### Scenario: Cash 与 buying power 边界保持清晰
- **WHEN** Alpaca account data 包含 cash 和 buying power
- **THEN** cash 可以作为 broker-shaped wallet cash context 的验证输入
- **AND** buying power 只记录为 broker context 或验证说明
- **AND** buying power 不被断言为 wallet cash ledger truth

#### Scenario: Fill 回放保持幂等
- **WHEN** Alpaca-shaped fill 或 recorded execution 被回放到本地 wallet state
- **THEN** 它使用账户范围内稳定的 source key
- **AND** 重放同一个 source key 不会重复产生 API 可见的 cash、position、execution 或 ledger 影响

#### Scenario: API 读出结果覆盖核心 wallet facts
- **WHEN** 本地 wallet state 已经由 Alpaca-shaped 数据 seed 或 ingestion 产生
- **THEN** E2E validation 通过 API route 读取 account、cash balances、positions、ledger entries、paper orders 和 paper executions
- **AND** 响应证明 API 可见状态与 wallet service 状态一致

### Requirement: 敏感信息不进入测试产物

QuantAgent SHALL 防止 Alpaca credentials 和真实 broker identifiers 被提交、记录到日志或写入 E2E validation 断言。

#### Scenario: 测试产物只使用占位 identifier
- **WHEN** 为 E2E validation 新增 fixtures、snapshots、logs 或 assertions
- **THEN** 它们使用 `acct_redacted`、`order_redacted_1` 或 `activity_redacted_1` 等稳定占位符
- **AND** 它们不包含真实 API key、secret key、account id、order id、client order id 或完整第三方原始响应

#### Scenario: PR 说明记录验证范围
- **WHEN** 准备 implementation PR
- **THEN** PR 说明写明是否运行离线 E2E
- **AND** PR 说明写明是否运行真实 Alpaca paper E2E smoke
- **AND** PR 说明写明是否提交过 paper order
- **AND** PR 说明明确重复 live trading、官方 Alpaca plugin、runtime adapter promotion 和 broker reconciliation 均不在范围内
