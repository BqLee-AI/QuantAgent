## 背景

当前仓库已经明确 `apps/api` 是 HTTP 边界，`packages/core` 承载共享配置、数据库、错误和领域基础能力。issue #120 要解决的不是交易终端或真实券商接入，而是先定义后端第一版账户资产事实层，使虚盘账户、现金余额、持仓、虚拟订单、虚拟成交、账本和 Policy Gate 查询有稳定边界。

本设计采用 issue #120 中确认的推荐范围：V1 只支持虚盘账户闭环；首批 instrument / market 采用股票类 spot 抽象，不提前覆盖加密货币、期货、期权、保证金或复杂交易时段；多币种仅支持虚拟余额和展示折算，不做真实换汇；不实现 broker snapshot / reconciliation；不新增复杂账户级风控配置表；不在 OpenSpec 阶段单独手写 `packages/contracts` schema。

本 change 归档前的已交付范围收窄为 `packages/core` 内可复用的 wallet core 能力：领域对象、ORM / repository、迁移、service、wallet facts 查询与核心测试。`apps/api` 薄封装、Policy Gate consumer 接入和跨模块集成验证继续由后续 issue 承接，不再作为本 change 的 must-have 交付项。

## 目标与非目标

**目标：**

- 在 `packages/core` 下定义 wallet / portfolio 领域边界。
- V1 只支持 `paper` 虚盘账户模式，不连接真实券商账户。
- 支持多币种虚拟现金余额，区分 `total`、`available`、`locked`、`unsettled` 和 `currency`。
- 支持虚拟持仓模型与现金余额分离，保留 instrument、market、side、quantity、average_cost、market_value、currency 和 unrealized_pnl 等信息。
- 支持虚拟订单与虚拟成交分离，避免用持仓表记录所有交易变化。
- 支持 append-only wallet ledger，用于记录虚拟交易、费用、资金划转、分红、利息、汇兑和人工调整。
- 支持幂等处理 paper execution，避免重复 payload 导致重复入账。
- 为 Policy Gate 提供可查询的账户模式、可用现金、锁定现金、未结算现金、可卖持仓和风险敞口事实。
- 明确 API 层只暴露资源和 DTO，不承载核心资产计算，不直接返回 ORM model。
- 明确真实 secret、完整账户号、真实交易密钥和私有策略参数不得进入普通 API 响应、日志或仓库。

**非目标：**

- 不实现真实自动下单、撤单、改单、换汇、资金划转或调仓。
- 不接入真实券商 API key、真实交易密钥、真实生产账户或 live trading。
- 不做 live read-only sync、broker snapshot、broker reconciliation 或 gated live execution。
- 不实现完整交易终端、复杂交易图表或前端下单工作台。
- 不实现自动仓位管理、自动止损止盈、组合优化、保证金模型、期货逐日盯市或期权希腊值。
- 不把 executor 插件硬编码进 core，不让插件直接持有数据库 session。
- 不把 wallet 核心逻辑放入 `apps/api` route、controller 或 DTO 层。
- 不要求在本 change 内完成 `apps/api` 的 route / DTO 薄封装、Policy Gate consumer 接入或跨模块集成验证。
- 不将 “先 OpenSpec-only PR、后实现 PR” 误写成本 change 已实际执行的门禁事实；当前 PR 为 artifacts 与 `packages/core` 实现合并 review 的实现 PR，相关 gate 说明只保留为仓库推荐流程，不再表述为本次已先行完成的前置审批。

## 决策

### 1. Wallet core 落在 packages/core，API 保持薄

V1 的领域模型、账本规则、幂等入库、余额和持仓计算、风控查询能力 SHOULD 落在 `packages/core`。API route 只负责鉴权、DTO、响应 envelope、HTTP 错误映射和调用 core service。

本次归档只冻结 core 侧边界，不把 API route / DTO 本身纳入已交付能力。

替代方案是把账户资产计算写入 `apps/api` route。该方案会让 worker、scheduler、executor、Policy Gate 或后续插件复用困难，并违反 API 层不承载核心领域逻辑的边界，因此不采用。

### 2. V1 只支持 paper account

`TradingAccount.mode` 在 V1 SHALL 只支持 `paper`。`live`、`read_only_live` 或其他真实账户模式只能作为后续 phase 的设计方向，不能被 V1 API 或持久化逻辑启用。

替代方案是同时设计并实现实盘只读账户。该方案会引入真实账户标识、broker secret、外部快照、同步批次和对账记录，与 “only 虚盘，不操作实盘” 的 V1 边界冲突，因此不采用。

### 3. 现金、持仓、订单、成交和账本分离

V1 SHALL 将 `CashBalance`、`Position`、`PaperOrder`、`PaperExecution` 和 `WalletLedgerEntry` 分离表达。current snapshot 用于查询当前事实，ledger 用于审计、回放和对账，不能用单张余额表替代账本。

替代方案是把现金、持仓和交易变化混入一张 balance 表。该方案会让虚拟成交、费用、人工调整、分红、利息和汇兑难以审计，也不利于后续对账，因此不采用。

### 4. Ledger 按 append-only 思路设计

`WalletLedgerEntry` SHALL 只追加业务历史，记录来源、类型、币种、金额、关联虚拟订单或虚拟成交、发生时间和幂等来源。修正错误时应通过 reversal 或 adjustment entry 表达，不覆盖历史记录。

替代方案是直接更新历史账本记录或只保留 current snapshot。该方案会破坏回放和审计能力，因此不采用。

### 5. Paper simulator 负责模拟执行，wallet core 负责事实层

Paper simulator / paper executor SHOULD 负责根据输入请求产生虚拟订单和虚拟成交。Wallet core SHALL 负责校验账户模式、幂等接收虚拟成交、更新现金和持仓事实、写入账本，并提供查询接口。

官方路径是：paper simulator / paper executor 产生虚拟订单或虚拟成交命令，调用 wallet core 的受控入口；wallet core 在同一事务边界内持久化 `PaperOrder`、`PaperExecution`、`WalletLedgerEntry`、`CashBalance` 和 `Position` 的变化。禁止 executor 插件直接持有数据库 session、直接写 wallet 表，或把余额、持仓、账本作为插件私有事实层保存。

替代方案是让 executor 插件内部私有保存余额和持仓。该方案会导致 Policy Gate、API 和审计无法查询统一事实层，因此不采用。

### 6. Wallet 暴露 facts 查询边界，但不负责外层消费接入或放行决策

Wallet core SHOULD 提供账户模式、可用现金、锁定现金、未结算现金、持仓数量、可卖持仓、单标的敞口和 paper execution permission 等 facts。最终是否允许任何后续动作仍由 Decision / Policy Gate 根据权限、风险、审批和用户策略决定。

本次归档要求 core 侧提供稳定 facts 查询接口；外层 Policy Gate / risk check consumer 的接线属于后续 issue。

替代方案是在 wallet core 中持久化完整风控配置并自行判断交易是否放行。该方案会提前复杂化 Policy Gate / user policy / wallet 的边界，因此 V1 不采用。

### 7. 多币种支持停留在虚拟余额和展示折算

V1 SHALL 支持多币种虚拟现金余额和用于展示折算的 `FxRateSnapshot`。原始金额仍保留原币种。V1 不提供真实换汇动作，也不模拟自动换汇订单。

替代方案是支持多币种余额和自动换汇动作。自动换汇本身是交易行为，需要审批、执行器、风控和审计，超出 V1 范围，因此不采用。

### 8. Broker snapshot 和 reconciliation 推迟

`BrokerConnection`、`BrokerSnapshot`、`ReconciliationRecord` 只作为后续 live read-only sync phase 的候选模型，不进入 V1 实现范围。后续如果引入 `external_*` 字段，必须补充幂等唯一约束，避免重复同步导致重复入账。

替代方案是在 V1 同时设计并实现最小 broker snapshot 和 reconciliation。该方案会把真实券商同步和对账边界提前带入 V1，与不连接真实券商账户的范围冲突，因此不采用。

### 9. Contracts 暂不单独手写 schema

V1 OpenSpec 阶段 SHOULD 定义 API 资源和 DTO 草案。实现阶段通过 FastAPI/OpenAPI 路线同步跨端契约，不在本 change 中单独提交 `packages/contracts/schemas/wallet.schema.json`。

替代方案是 OpenSpec 阶段同步手写 contracts schema。该方案容易在 API 字段仍处于评审时制造 contracts 与实现漂移，因此不采用。

### 10. 明确事实层、证据层和查询投影

V1 SHALL 区分钱包事实、证据和查询投影：

- `TradingAccount` 是账户配置和模式事实。
- `PaperOrder`、`PaperExecution` 和 `WalletLedgerEntry` 是虚盘交易和账务变化证据。
- `CashBalance` 与 `Position` 是当前查询投影，必须由受控入账流程维护，不能绕过账本成为唯一历史真源。
- `FxRateSnapshot` 是折算证据，只能用于展示折算和历史回放，不能覆盖原币种事实。
- API DTO、前端视图和 OpenAPI 生成物都是派生层，不能反向覆盖 wallet core 的领域事实。

实现阶段如果发现 snapshot 与 ledger 不一致，应优先把不一致暴露为错误、告警或后续 reconciliation 需求，不能静默以 API 视图或前端计算结果修正 core 事实。

### 11. 数值精度使用十进制定点语义

V1 涉及金额、数量、价格、费率、汇率和成本的字段 SHOULD 使用十进制定点语义。Python 实现应使用 `Decimal` 或等价的定点类型，数据库实现应使用适合金融数值的 `Numeric` / `Decimal` 类型；不得用二进制浮点数作为持久化或核心计算类型。

具体 scale、precision 和 rounding policy 可在实现阶段根据数据库与 API DTO 统一确定，但必须在迁移、领域对象、DTO 和测试之间保持一致。

### 12. 幂等边界必须有稳定来源键

V1 paper execution 入账 SHALL 基于稳定幂等来源判断重复。实现阶段应为 `PaperExecution` 或入账命令定义可持久化的 idempotency key / source reference，并在同一账户范围内保证唯一。

幂等键的来源可以是 paper simulator 生成的 execution reference，也可以是 wallet core 为输入命令生成的稳定 reference；无论采用哪种方式，重复提交同一来源不得重复更新 `CashBalance`、`Position` 或 `WalletLedgerEntry`。

### 13. 初始化和人工调整走受控入口

V1 可以支持虚盘账户的初始入金、出金和人工调整，但这些操作 SHALL 通过 wallet core 的受控命令写入 ledger，并同步维护 current snapshot。实现不得直接修改 `CashBalance` 或 `Position` 来绕过 ledger。

这些人工入口仍然只作用于虚盘账户，不代表真实资金划转、真实 broker transfer 或实盘账户调整。

## 风险与取舍

- [风险] V1 不覆盖加密货币、期货、期权或保证金，后续模型可能需要扩展。  
  -> 缓解：V1 保留 market、instrument、currency、side 和 FxRateSnapshot 等扩展位，但不提前实现复杂资产类别。

- [风险] 不做 broker snapshot / reconciliation 会让 reviewer 担心后续实盘同步如何落地。  
  -> 缓解：design 明确这些对象属于后续 phase，并要求 live read-only sync 单独 change 收口。

- [风险] API 资源草案可能被误解为已经可以下真实订单。  
  -> 缓解：本次归档 stable spec 不把 API 资源本身列为已交付 requirement，只保留 core / paper-only 边界与后续 API 非目标说明。

- [风险] 只提供 facts 而不提供复杂风控配置，Policy Gate 初期能力有限。  
  -> 缓解：V1 保持 wallet 事实层定位，账户级风控配置与 Policy Gate consumer 接入由后续 issue / change 单独定义。

- [风险] 文档中历史 “dry-run executor” 表述可能和本 change 的 “虚盘账户事实层” 混淆。  
  -> 缓解：本 change 内统一使用 “only 虚盘，不操作实盘”，并在 tasks 中安排后续 docs/design 中 wallet / asset-state 相关表述收敛检查；不把 executor dry-run 作为系统阶段能力的通用表述误删。

- [风险] 实现者可能把 `CashBalance` / `Position` 当成可直接写的事实表。  
  -> 缓解：design 和 spec 明确 snapshot 是查询投影，所有业务变化必须通过受控入账或人工调整命令追加 ledger。
