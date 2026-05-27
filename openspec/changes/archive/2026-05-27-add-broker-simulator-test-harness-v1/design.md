## 背景

issue #157 的目标不是再补一层内部单测，也不是直接实现真实券商 adapter，而是验证 `packages/core` 的 Portfolio Wallet Core V1 是否能被一个“外部券商形态”的受控输入稳定驱动。当前 stable spec 已经冻结 paper-only 账户、现金、持仓、paper order、paper execution、append-only ledger 和 execution 幂等边界，但还缺一套站在系统边界外侧的 contract-style 测试，把外部账户快照、成交回报和错误路径映射到 wallet core 的受控入口。

仓库规则同时给了两个重要约束：

- wallet facts、ledger 和幂等入账必须留在 `packages/core`，不能绕过 core service 直接写表。
- plugin 系统未来必须通过 `plugin.yaml` 和 Registry 进入系统，但当前不能为了测试 harness 提前固化完整 plugin SDK、runtime 安装或真实 executor 行为。

因此第一版 design 采用“broker-shaped adapter contract + in-memory/local fixture simulator”的方式，落在 `packages/core` 测试边界。它先证明外部数据驱动 wallet core 的价值，再为未来 Alpaca / Futu / IBKR 等真实 paper adapter 准备一套可复用的 contract test 雏形。这里的“broker-shaped”强调测试输入和断言上下文站在外部适配器一侧，而不是要求本轮新增 broker snapshot import 或同步存储能力。

## 目标与非目标

**目标：**

- 定义最小 broker simulator / adapter-shaped 测试协议，表达账户、现金、持仓、订单、成交和 broker error 输入。
- 通过 wallet core 的 service-level 受控入口验证 full fill 入账、重复 execution 幂等、账本 append-only 和金额定点语义。
- 证明 harness 可以站在 plugin 或 adapter 的形状上驱动 wallet core，但不要求第一版引入稳定 plugin SDK。
- 用无网络、无真实密钥、可在 CI 运行的测试覆盖 fee、多币种字段、rejected 或 insufficient cash 等关键场景。
- 为后续真实 paper broker adapter 提供 contract-style 测试模板，而不是让每个 adapter 自己重新发明 wallet 验证语义。

**非目标：**

- 不连接真实券商 API，不保存真实 API key、OAuth token、真实账户号或生产配置。
- 不实现真实下单、撤单、改单、换汇、资金划转、live trading 或 broker snapshot / reconciliation。
- 不把 simulator 逻辑写进 `apps/api` 或通过 route 直接入账。
- 不实现 broker snapshot sync、external cash/position reconciliation 或新的外部状态持久化模型。
- 不在第一版中强制新建 `packages/adapters`、完善 `packages/plugin-sdk`，或实现完整 `runtime/plugins` 集成。
- 不把 partial fill、multi-fill、replace、cancel、expired 等完整订单状态机作为本轮必收范围。

## 决策

### 1. 第一版 harness 落在 `packages/core` 测试边界，而不是插件运行时

第一版 SHALL 以 `packages/core/tests/**` 为主要实现和验证边界。这里可以放 simulator fixture、adapter-shaped contract helper、execution payload builder 和说明文档，但不要求它成为正式 runtime plugin。除非为测试暴露既有 service seam 所必需，本轮默认也不修改 `apps/api`、`plugins/`、`runtime/plugins/` 或 `packages/plugin-sdk`。

替代方案是直接做一个官方 broker simulator plugin，或者把样例落到 `runtime/plugins`。这会同时拉入 manifest、Registry、配置校验和生命周期问题，扩大评审面，也会和 issue #152 的 executor plugin 方向重叠，因此本轮不采用。

### 2. 以“broker-shaped contract”驱动 wallet core，而不是内部 service 直接造状态

第一版 SHALL 定义一组最小外部输入对象或测试协议，用来表达：

- broker account snapshot
- cash balances by currency
- positions by instrument / market
- paper order intent / broker order view
- broker execution event
- broker-side reject / insufficient cash / generic broker error

这些对象不必一开始就成为稳定公开 SDK，但测试必须从这种外部形状进入，再映射到 wallet core 的受控入口。这里的账户、现金、持仓形状首先是“broker 返回了什么”和“wallet 最终应呈现什么”的测试上下文，不等于本轮要给 production code 新增外部 snapshot import API。测试不得直接通过 repository 预写现金、持仓或账本来“伪造已入账结果”。

### 3. execution 幂等以账户范围内稳定 source key 为真源

第一版 SHALL 要求 broker execution 输入携带账户范围内稳定的 `external_execution_id`、`source_key` 或等价幂等键。映射进入当前 core 时，该键应明确落到 `RecordPaperExecutionCommand.idempotency_key` 或等价 service seam。wallet core 接收同一幂等键的重复 execution 时，不得重复扣减现金、增加持仓、写入 paper execution 或追加 ledger entry。

替代方案是仅依赖测试内部对象 identity 或数据库自增主键判断重复。该方案不能表达真实外部系统重复回调、重复同步或重放场景，因此不采用。

### 4. Harness 只走 wallet core 受控入口，不允许绕库

Simulator contract tests SHALL 通过 `packages/core` 已有 `WalletService` 公开命令与查询方法，或与其应用同一领域规则的 service-level helper，提交 order / execution / adjustment 类输入。它们不得：

- 直接写 wallet ORM 表
- 直接修改 cash 或 position snapshot
- 绕过 ledger 追加历史
- 在 API route 中塞入 simulator 或 broker mapping
- 直接实例化 repository / ORM model 作为 harness 主入口

替代方案是为了测试方便，先把 fixture 直接插入数据库。该方案会削弱本 issue 的核心价值，即验证“外部输入 -> core 受控入口 -> 账本 / 持仓 / 现金一致性”的链路，因此不采用。

### 5. 第一版强制覆盖 full fill、duplicate execution、拒单/余额不足、fee、多币种和 Decimal 精度

第一版 contract tests SHALL 至少覆盖：

- 正常 full fill execution 入账
- duplicate execution 幂等，不重复改变 cash / position / ledger
- broker reject 或 insufficient cash，不产生错误入账
- fee 对现金与 ledger 的影响
- 多币种 cash 或 execution 字段映射
- Decimal / 定点语义，不引入 float 作为核心计算断言

对于 `reject` 或 `insufficient cash`，第一版允许用两种等价方式表达负路径：

- broker simulator 在 adapter 层直接返回拒绝/错误结果，因此 wallet core 不发生 execution 入账；
- broker-shaped 输入映射到 service-level 调用后抛出受控错误，并断言没有产生 cash / position / execution / ledger 副作用。

第一版不要求 wallet core 在本轮新增“像真实券商那样先验校验可用资金再决定拒单”的生产能力。partial fill 可以作为可选扩展，但不属于本轮必收标准。这样可以先验证地基，不把完整订单生命周期讨论提前拉入。

### 6. 保持 adapter / plugin-shaped 边界，但不提前固化 SDK 或新 package

第一版 SHOULD 在命名和测试结构上保留未来真实 adapter 可复用的 contract test 入口，例如 `run_wallet_broker_contract_suite(...)`、`BrokerSimulatorFixture` 或等价 helper。但它不要求当前就引入 `packages/adapters` 或完善 `packages/plugin-sdk`。如果需要定义 helper，helper 的职责应停留在“构造 broker-shaped 输入并触发 wallet service 调用”，而不是变成新的 production adapter 抽象。

替代方案是立刻新建正式 adapter package。该方案只有在已有明确复用方、导出 API 和依赖方向时才合理；当前 issue 只需要测试地基，因此不采用。

### 7. 本 change 不替代 #152，也不打开真实执行能力

issue #152 指向 Binance dry-run broker plugin 的具体样例；本 change 的目标更底层，是验证 wallet core 的外部接入式测试语义。第一版 harness 只证明 wallet core 可以被 broker-shaped 输入驱动，不证明某个具体 executor plugin、Registry 生命周期或真实 broker 接口已完成。

## 实现边界

- Canonical asset: `packages/core/src/quantagent/core/wallet/**` 中的 wallet service、domain model、repository 与 stable `portfolio-wallet-core-v1` spec。
- Harness layer: `packages/core/tests/**` 中的 simulator fixture、broker-shaped contract helper、测试说明与断言。
- Optional seam: 面向未来 adapter/plugin 的测试协议命名与 helper；当前不要求形成正式 SDK。
- Forbidden bypass:
  - 新增 broker snapshot sync、reconciliation 或外部账户镜像持久化模型
  - `apps/api` route 内实现 simulator 或 broker mapping
  - 直接写 wallet ORM / repository 伪造结果
  - 引入真实网络、真实 broker SDK、真实密钥或真实账户
  - 混入 live broker sync、broker snapshot、reconciliation、真实执行或 #152 的 executor plugin 施工

## 风险与取舍

- [风险] 当前 wallet core 入口如果过于内聚在内部 service，可能需要先整理测试可注入 seam。  
  -> 缓解：第一版优先复用现有 service / domain 命令入口，只在测试所需最小边界上补 helper，不扩大对外 API。

- [风险] 如果过早把测试协议写成“稳定 SDK”，后续真实 adapter 设计可能被第一版草率命名锁死。  
  -> 缓解：本轮只沉淀 contract-style 测试语义和 helper，不承诺它已经是长期公开 SDK。

- [风险] 仅在 `packages/core/tests` 落地，不能证明完整 plugin runtime 链路。  
  -> 缓解：issue 已明确第一版优先验证 wallet core 外部输入链路；plugin runtime 集成留给后续独立 change。

- [风险] partial fill 未进入必收，可能延后暴露订单生命周期问题。  
  -> 缓解：在 tasks 中把 partial fill 标为后续可选扩展，并确保 full fill、duplicate execution、fee 和拒单场景先可重复验证。

- [风险] 测试为了方便把外部字段直接贴 core 模型，导致“外部形状”价值不足。  
  -> 缓解：明确要求 contract tests 从 broker-shaped fixture 输入开始，再映射到 wallet core 受控入口，不允许直接以内部 snapshot 作为测试输入。
