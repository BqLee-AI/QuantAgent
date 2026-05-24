# Portfolio Wallet Core V1 Specification

## Purpose

定义 `packages/core` 中 Portfolio Wallet Core V1 的稳定能力边界：只支持虚盘账户的资产事实层、账本与幂等入账规则、多币种虚拟余额与持仓分离、FX 折算快照、wallet facts 查询边界，以及明确排除实盘同步、真实执行和 API 薄封装等后续能力。

## Requirements

### Requirement: Portfolio Wallet Core V1 只支持虚盘账户

QuantAgent SHALL define Portfolio Wallet Core V1 as a paper-account-only asset facts layer.

#### Scenario: 创建或查询 V1 账户模式
- **WHEN** V1 表达交易账户
- **THEN** 账户 mode 只能是 `paper`
- **AND** 任何 `live`、`read_only_live` 或真实券商账户模式都不属于 V1 可用能力

#### Scenario: V1 不连接真实券商账户
- **WHEN** wallet core 处理账户、余额、持仓、订单或成交
- **THEN** 它不连接真实券商 API
- **AND** 它不读取真实生产账户
- **AND** 它不执行真实下单、撤单、改单、换汇、资金划转或调仓

#### Scenario: only 虚盘，不操作实盘
- **WHEN** 文档或实现描述 Portfolio Wallet Core V1
- **THEN** 它应被描述为 “only 虚盘，不操作实盘”
- **AND** 不应把账户资产事实层简化描述为 only dry-run executor

### Requirement: V1 首批 market 范围限定为股票类 spot 抽象

Portfolio Wallet Core V1 SHALL use a stock-like spot instrument / market abstraction for the first phase without implementing complex asset classes.

#### Scenario: 表达 V1 虚拟标的和市场
- **WHEN** V1 表达虚拟订单、虚拟成交或虚拟持仓
- **THEN** 它使用 instrument、market、side、quantity、price 和 currency 等股票类 spot 所需字段
- **AND** 不要求实现加密货币、期货、期权、保证金、合约乘数、交割、逐日盯市或复杂交易时段语义

#### Scenario: 后续资产类别扩展
- **WHEN** 后续需要支持加密货币、期货、期权或保证金
- **THEN** 需要通过单独 OpenSpec change 扩展模型和验收
- **AND** 不能把这些资产类别能力隐含进 Portfolio Wallet Core V1

### Requirement: Wallet core 位于共享领域边界

QuantAgent SHALL keep wallet facts, ledger rules and portfolio calculations in shared core rather than API routes or executor-private state.

#### Scenario: executor 不私有保存资产事实
- **WHEN** paper simulator 或 paper executor 产生虚拟订单或虚拟成交
- **THEN** 它通过 wallet core 的受控入口提交虚拟订单或虚拟成交命令
- **AND** wallet core 负责持久化 `PaperOrder`、`PaperExecution`、`WalletLedgerEntry`、`CashBalance` 和 `Position` 的变化
- **AND** executor 插件不能直接持有数据库 session、直接写 wallet 表，或把余额、持仓和账本作为系统唯一事实私有保存

### Requirement: 多币种虚拟现金余额与持仓分离

Portfolio Wallet Core V1 SHALL represent virtual cash balances separately from virtual positions.

#### Scenario: 查询多币种现金余额
- **WHEN** 查询账户现金余额
- **THEN** 每个现金余额包含 `currency`、`total`、`available`、`locked` 和 `unsettled`
- **AND** 多个币种的余额以独立记录表达

#### Scenario: 查询虚拟持仓
- **WHEN** 查询账户持仓
- **THEN** 每个持仓包含 instrument、market、side、quantity、average_cost、market_value、currency 和 unrealized_pnl 等核心信息
- **AND** 持仓记录不被用来表达现金余额

#### Scenario: 现金和持仓不能混入同一 current balance 模型
- **WHEN** wallet core 存储当前资产事实
- **THEN** 现金余额和持仓 snapshot 使用分离模型
- **AND** 查询层可以聚合展示资产，但不能以一张混合 current balance 表替代领域边界

#### Scenario: 数值字段使用定点语义
- **WHEN** wallet core 表达金额、数量、价格、费用、成本、汇率或市值
- **THEN** 核心计算和持久化使用十进制定点语义
- **AND** 不使用二进制浮点数作为核心计算或持久化类型

### Requirement: 虚拟订单与虚拟成交分离

Portfolio Wallet Core V1 SHALL distinguish paper orders from paper executions.

#### Scenario: 记录虚拟订单请求
- **WHEN** paper simulator 接收虚拟交易请求
- **THEN** 系统可记录 `PaperOrder`
- **AND** `PaperOrder` 表达账户、instrument、market、side、order_type、quantity、可选 limit_price、status、requested_at 和可选 completed_at

#### Scenario: 记录虚拟成交结果
- **WHEN** paper simulator 产生虚拟成交
- **THEN** 系统可记录 `PaperExecution`
- **AND** `PaperExecution` 表达账户、订单、instrument、market、side、quantity、price、fee_amount、fee_currency 和 executed_at

#### Scenario: 订单状态不替代成交事实
- **WHEN** 查询虚拟交易历史
- **THEN** 订单请求和成交结果可以分别查询
- **AND** 订单状态不能作为唯一成交事实来源

### Requirement: Wallet ledger 是 append-only 事实历史

Portfolio Wallet Core V1 SHALL use append-only ledger entries for auditable account history.

#### Scenario: 记录账本 entry
- **WHEN** 发生虚拟交易、费用、资金划转、分红、利息、汇兑或人工调整
- **THEN** wallet core 追加 `WalletLedgerEntry`
- **AND** entry 包含 account、type、currency、amount、source、occurred_at 和必要关联对象

#### Scenario: 修正历史使用调整 entry
- **WHEN** 需要修正既有账本影响
- **THEN** 系统通过 reversal 或 adjustment entry 表达修正
- **AND** 不覆盖或删除既有业务历史来改变回放结果

#### Scenario: Snapshot 不能替代 ledger
- **WHEN** wallet core 维护现金或持仓 snapshot
- **THEN** snapshot 用于当前查询
- **AND** ledger 用于审计、回放和对账
- **AND** 系统不能只保存 current snapshot 而缺少账本历史

#### Scenario: 业务变化不能绕过 ledger
- **WHEN** 系统处理虚拟入金、出金、交易、费用、分红、利息、汇兑或人工调整
- **THEN** 这些变化通过 wallet core 的受控入口追加 ledger
- **AND** 不直接修改 cash 或 position snapshot 来绕过账本历史

### Requirement: 虚拟成交入账必须幂等

Portfolio Wallet Core V1 SHALL avoid duplicate balance, position and ledger updates for the same paper execution source.

#### Scenario: 虚拟成交具有稳定幂等来源
- **WHEN** wallet core 接收 paper execution 入账请求
- **THEN** 请求包含或生成账户范围内稳定的幂等来源键
- **AND** 该来源键可持久化并用于重复提交判断

#### Scenario: 重复提交同一虚拟成交
- **WHEN** 同一 paper execution payload 或幂等来源被重复提交
- **THEN** wallet core 不重复更新现金余额
- **AND** 不重复更新持仓 snapshot
- **AND** 不重复追加 wallet ledger entry

#### Scenario: 入账更新在同一事务边界内完成
- **WHEN** wallet core 接收新的有效 paper execution
- **THEN** 现金 snapshot、持仓 snapshot、paper execution 记录和 ledger entry 在同一事务边界内保持一致
- **AND** 任一关键写入失败时不得留下部分入账状态

### Requirement: Fx rate snapshot 只用于虚盘折算和回放

Portfolio Wallet Core V1 SHALL support FX rate snapshots for virtual asset presentation and historical replay without enabling real FX actions.

#### Scenario: 保存汇率快照
- **WHEN** 系统需要展示多币种资产折算
- **THEN** 可以记录 `FxRateSnapshot`
- **AND** snapshot 包含 from_currency、to_currency、rate、source 和 captured_at

#### Scenario: 原币种金额必须保留
- **WHEN** 使用汇率快照进行展示折算
- **THEN** 原始 cash、position、execution 或 ledger 金额仍保留原币种
- **AND** 折算结果不能替代原始事实

#### Scenario: V1 不执行真实换汇
- **WHEN** 账户存在多个币种余额
- **THEN** V1 不提供真实换汇、自动换汇或跨币种资金调拨动作

### Requirement: Wallet facts 可供 Policy Gate 查询

Portfolio Wallet Core V1 SHALL expose account facts needed by Decision / Policy Gate while leaving final authorization to Decision / Policy Gate.

#### Scenario: Policy Gate 查询账户事实
- **WHEN** Policy Gate 或 risk check 需要资产事实
- **THEN** wallet core 可提供账户模式、可用现金、锁定现金、未结算现金、持仓数量、可卖持仓、单标的敞口和 paper execution permission

#### Scenario: Wallet 不绕过 Policy Gate
- **WHEN** 后续动作可能产生执行副作用
- **THEN** wallet facts 只能作为 Policy Gate 输入
- **AND** wallet core 不单独决定真实或高风险动作是否放行

### Requirement: 实盘同步和对账属于后续 phase

Portfolio Wallet Core V1 SHALL leave broker connection, broker snapshot and reconciliation capabilities out of V1 implementation.

#### Scenario: BrokerConnection 不进入 V1
- **WHEN** 设计后续真实券商连接能力
- **THEN** `BrokerConnection` 可以作为后续 phase 候选模型
- **AND** V1 不保存真实 broker plugin secret、真实账户连接或同步状态

#### Scenario: BrokerSnapshot 和 ReconciliationRecord 不进入 V1
- **WHEN** 设计 live read-only sync、broker snapshot 或 reconciliation
- **THEN** 这些能力需要单独 OpenSpec change
- **AND** V1 不实现 broker snapshot 存储、同步批次或对账记录

#### Scenario: 后续外部同步必须幂等
- **WHEN** 后续 phase 引入 `external_*` 字段或 broker snapshot
- **THEN** 设计必须包含幂等唯一约束
- **AND** 不能因重复同步导致重复入账
