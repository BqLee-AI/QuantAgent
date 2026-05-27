## 背景

issue #158 的目标不是把 QuantAgent 变成 Alpaca broker client，也不是把真实 broker 能力纳入 Portfolio Wallet Core V1，而是在 #157 的本地 broker simulator harness 之后，用真实第三方 paper API 做一次受控 spike。这个 spike 要回答一个具体问题：#157 的 broker-shaped contract、字段映射、错误处理、幂等 source key 和 wallet ingestion 入口，面对 Alpaca paper 这类真实 API 时是否存在明显断层。

仓库已有边界给出三个硬约束：

- Portfolio Wallet Core V1 是 paper-account-only asset facts layer，不连接真实券商，不做 live trading。
- 插件 / executor 长期需要通过 Registry 和 `plugin.yaml` 进入系统，但 issue #158 不产品化 Alpaca official plugin。
- #157 的 broker simulator harness 是本 change 的 contract 真源；Alpaca 只能校准真实 API 差异，不能反向扩大 wallet core 或 adapter SDK 范围。

因此本 design 采用“测试 / spike 边界内的 Alpaca paper adapter helper + mock/recorded contract tests + 显式外部 smoke test”方案。默认测试仍必须无网络、无 secret、可重复；真实 Alpaca paper 访问只在开发者或受控 CI 显式提供 credentials 和开关时运行。除非本文明确列为后续正式化工作，当前 phase 的规范性资产只有本 change 的 OpenSpec artifacts、#157 的 broker simulator harness 和后续实现中的测试 / spike 文件。

## 目标与非目标

**目标：**

- 读取 Alpaca paper account、cash / buying power、positions 和 orders，并映射到 #157 的 broker-shaped contract 语义；其中 `cash` 可作为现金字段候选，`buying_power` 只能作为 broker account context 或风险输入证据，不得直接当作 wallet cash ledger 真源。
- 用 mock transport 或脱敏 recorded response 覆盖 account activities / fills 中与 wallet execution 入账相关的最小字段。
- 验证 paper base URL、认证 header、超时、网络失败、错误响应和 secret 脱敏规则。
- 可选地在额外显式开关下提交一笔受 OpenSpec 上限约束的 Alpaca paper order，并用 QuantAgent 生成的 `client_order_id` 回查订单状态。
- 明确后续正式 paper broker adapter 的配置、脱敏、测试开关和 PR 验证说明模板。

**非目标：**

- 不接入 Alpaca live trading endpoint，不提供 live endpoint fallback。
- 不提交真实 Alpaca API key、secret、account id、order id、完整响应 fixture 或本地 `.env`。
- 不把 Alpaca paper smoke test 作为默认 CI 必跑测试。
- 不做真实资金操作、真实下单能力产品化、撤单、改单、换汇、资金划转或 broker reconciliation 持久化。
- 不扩展 Portfolio Wallet Core V1 到 margin、options、crypto、short selling 或复杂资产类别。
- 不把 Alpaca spike 放入 `packages/adapters` 作为稳定导出 API，也不放入 `plugins/executors` 作为官方 executor plugin。
- 不绕过 Decision / Policy Gate；本 issue 不建立生产执行链路。

## 决策

### 1. 严格依赖 #157 完成后实施

本 change SHALL 要求 #157 的 `add-broker-simulator-test-harness-v1` 已完成后才能开始实现。完成判定是：`packages/core/tests/wallet_broker_simulator_harness.py`、`packages/core/tests/test_wallet_broker_simulator_harness.py` 和 `packages/core/tests/README.md` 中的 broker simulator harness 已存在，且实现者能够复用 `BrokerSimulatorHarness`、`BrokerSimulatorFixture`、`BrokerSimulatorOrderInput`、`BrokerSimulatorExecutionInput.source_key`、`BrokerSimulatorErrorInput` 与 `WalletService.ingest_paper_execution` 这条 contract 路径。Alpaca spike 的职责是校准真实 paper broker 差异，而不是先定义内部 broker contract。

替代方案是在 #157 OpenSpec 审核后并行实施 Alpaca spike。该方案能更早接触真实 API 字段，但容易让外部 API 反向影响未冻结的 wallet contract，因此本轮不采用。

### 2. Alpaca adapter helper 落在测试 / spike 边界

第一版 SHALL 把 Alpaca adapter helper、配置解析、mock transport、脱敏 recorded response 和外部 smoke test 放在测试 / spike 边界，默认落到 `packages/core/tests/**` 并与 #157 harness 相邻。它不作为 runtime adapter 导出，不建立 `packages/adapters` 正式 API，不新增官方 `plugins/executors` Alpaca plugin。

如果实现中确实需要生产代码 seam，必须先证明 #157 现有 `WalletService` 入口无法表达该测试，并把变更限制在 wallet core 已有 paper-only 受控入口的最小补强；不得新增 broker connection、secret 持久化、runtime adapter registry 或 plugin lifecycle。任何正式 adapter package、plugin SDK 或 Registry lifecycle 都应拆后续 issue / OpenSpec。

### 3. Paper-only URL 是硬边界

Alpaca paper base URL SHALL 固定校验为 `https://paper-api.alpaca.markets`。外部 smoke test、adapter helper 和配置解析不得把 live trading endpoint 作为默认值、fallback 或可接受目标。若实现允许通过 `ALPACA_PAPER_BASE_URL` 覆盖默认值，该变量只能等于 `https://paper-api.alpaca.markets`；任何其他 host、scheme 或 path 都必须让外部 smoke skip 或 fail fast，并在原因中避免输出 credentials。

该约束的目的不是保证 Alpaca paper 行为等同真实市场，而是防止 spike 误连 live endpoint 或让 reviewer 误解为 live broker 能力已经安全可用。

### 4. Credentials 只来自受控注入，缺失时默认 skip

Alpaca credentials SHALL 只从环境变量或受控 CI secret 注入读取。实现使用的变量名固定为 `APCA_API_KEY_ID` 与 `APCA_API_SECRET_KEY`，并由 adapter helper 映射为 `APCA-API-KEY-ID` / `APCA-API-SECRET-KEY` request headers。仓库不得提交真实 `.env`、API key、secret、account id、order id 或完整原始响应。

默认测试 SHALL 不访问网络、不需要 credentials。外部只读 smoke 只有在 `QUANTAGENT_ALPACA_PAPER_SMOKE=1`、paper base URL guard 通过、`APCA_API_KEY_ID` 和 `APCA_API_SECRET_KEY` 同时存在时运行；缺失任一条件时必须 skip 并给出非敏感原因。日志、异常、断言和 PR 说明不得输出 secret 原文。

### 5. Smoke test 分为只读默认外部 smoke 与额外 order submit smoke

显式启用外部 smoke 后，第一层 SHALL 只读访问 Alpaca paper account、positions 和 orders，验证认证、base URL、超时和基础字段映射。只读 smoke 不得调用 order submit、cancel、replace 或任何写接口，也不得因为读取到 account / position / order 而写入 wallet state。

提交 paper order SHALL 是第二层额外显式可选 smoke，不属于默认验收。它必须同时满足：

- 单独的 order smoke 开关已启用。
- 使用 paper base URL 且 URL guard 通过。
- symbol 命中测试白名单。
- notional 或 quantity 不超过硬上限：使用 notional 时 `notional <= 5 USD`，使用 quantity 时 `quantity <= 1`；如果目标 symbol 不支持该下单形态，应 skip order submit，而不是提高上限。
- request 使用 QuantAgent 生成的 `client_order_id`，并用该 id 或返回的 paper order id 回查状态。
- 测试和 PR 说明记录是否实际提交过 paper order。

第一版不覆盖 cancel、replace、多订单生命周期或真实成交保证。真实 paper order 不一定成交，不能把真实 fill 作为外部 smoke 必然验收。

### 6. Fills / activities 与错误路径必须可离线验证

Alpaca account activities / fills 中与 wallet 入账有关的字段映射 SHALL 用 mock transport 或脱敏 recorded response 覆盖。该测试必须在无网络、无 credentials 环境下运行，且 fixture 不得包含真实 account id、order id、secret、完整原始响应或可反查个人账户的信息。脱敏 fixture 只能保留实现映射必需字段；所有 identifier 使用稳定占位值，例如 `acct_redacted`、`order_redacted_1`、`activity_redacted_1`。

错误路径 SHALL 至少覆盖认证失败、invalid symbol、insufficient buying power、timeout / external unavailable，并验证错误映射和脱敏结果。错误测试不能依赖真实 Alpaca 服务返回某个实时错误。

### 7. Adapter 不直接写 wallet 表

Alpaca adapter helper SHALL 只把 broker-shaped account、position、order、fill / activity 数据映射到 #157 contract 语义。任何 execution 入账都必须构造 `BrokerSimulatorExecutionInput` 或等价 broker-shaped execution，并通过 #157 harness / `WalletService.ingest_paper_execution` 进入 wallet core 的 ledger 和 idempotency 规则。实现不得直接插入或修改 wallet ORM 表，不得直接改 cash / position snapshot，不得绕过 wallet service。

如果 Alpaca fill / activity 映射得到 external execution source key，该 key MUST 映射到 #157 / wallet core 的账户范围内稳定 idempotency source。重复同步或重复回放同一 fill 不得重复入账。

## 实现边界

- Canonical contract: #157 的 broker simulator test harness artifacts 和实现结果，具体包括 `BrokerSimulatorHarness`、`BrokerSimulator*` 输入 shape、`source_key` -> `idempotency_key` 映射和 `WalletService` 入账路径。
- Spike helper: `packages/core/tests/**` 下的 Alpaca paper adapter helper、mock transport、脱敏 fixture 和外部 smoke tests。
- External read-only smoke: 默认 skip；仅 `QUANTAGENT_ALPACA_PAPER_SMOKE=1`、paper base URL guard 和 credentials 同时满足时访问 Alpaca paper API。
- External order submit smoke: 默认 skip；除只读 smoke 的全部条件外，还必须设置 `QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE=1` 并满足 symbol 白名单和下单上限。
- Forbidden runtime expansion:
  - 新建正式 Alpaca runtime adapter API。
  - 新建官方 Alpaca executor plugin。
  - 接入 live endpoint 或提供 live fallback。
  - 在 API route、plugin runtime 或 wallet repository 内实现 spike 逻辑。
  - 持久化 broker snapshot、reconciliation batch 或真实 broker connection secret。

## 风险与取舍

- [风险] Alpaca paper API 字段与 #157 contract 不完全一致。  
  -> 缓解：只在 spike 文档和测试中记录差异；需要改变 contract 时另开后续 issue / OpenSpec，不在本 change 中反向放宽 wallet core。

- [风险] 外部 smoke 受网络、credentials、Alpaca paper 环境状态影响。  
  -> 缓解：默认 skip，关键映射和错误路径全部用 mock transport 或脱敏 recorded response 覆盖。

- [风险] paper order submit 可能被误解为产品下单能力。  
  -> 缓解：提交订单 smoke 需要额外显式开关、白名单、上限和 PR 说明，并保持在测试 / spike 边界。

- [风险] 脱敏不彻底导致 secret 或账户信息进入日志 / fixture。  
  -> 缓解：测试必须覆盖 secret、account id、order id 和错误响应脱敏；fixture 只保留最小字段和替换后的占位值。

- [风险] 将 spike helper 过早设计为稳定 SDK。  
  -> 缓解：命名和文档明确 experimental / spike，正式 `packages/adapters` 或 plugin SDK 由后续 change 决定。
