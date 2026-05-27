## Context

当前仓库已经形成三条相邻但尚未端到端串起来的能力边界：

- `portfolio-wallet-core-v1` 提供虚盘 wallet 事实层、账本、paper order、paper execution 和 `WalletService` 受控入口。
- `add-portfolio-wallet-api-v1` 在 `apps/api` 暴露 wallet 只读 HTTP route，并验证鉴权、DTO、envelope、错误映射和 OpenAPI。
- `spike-alpaca-paper-adapter` 在 `packages/core/tests/**` 的测试 / spike 边界内验证 Alpaca paper 的 paper-only URL、credentials、只读 smoke、脱敏、字段映射和 fill -> wallet ingestion 的离线 contract。

这些验证仍是分段的：Alpaca paper smoke 能证明真实 paper endpoint 可读，API route tests 能证明 wallet endpoints 可用，但还没有一个受控验证证明真实 broker-shaped 数据进入 wallet 后，既有 API route 能读出一致的 wallet 状态。

本 change 的职责是补这条验证链路，不是把 Alpaca 接入上升为正式 runtime adapter。

## Goals / Non-Goals

**Goals:**

- 新增默认离线的端到端验证：构造 Alpaca-shaped account / position / order / fill 数据，经 wallet service 入账后，通过 `apps/api` wallet endpoints 读取并断言一致。
- 新增可选外部 smoke：在显式开关和 Alpaca paper credentials 存在时，读取真实 Alpaca paper account / positions / orders，将其转换为脱敏派生的本地测试 wallet 输入后通过 API 读出。
- 保持所有外部 smoke 默认 skip；无网络、无 credentials、无 `.env` 时本地测试和 CI 仍可通过。
- 保持 API 层只读：测试可以在测试进程内 seed wallet state，但不新增 API 写 endpoint。
- 记录真实外部验证是否触达 Alpaca paper、是否提交 paper order、是否使用 mock fill，以及哪些字段被视为 broker context 而非 wallet ledger truth。

**Non-Goals:**

- 不新增 Alpaca API route。
- 不新增正式 `packages/adapters`、plugin SDK、官方 Alpaca executor plugin 或 Registry lifecycle。
- 不接入 live trading endpoint，不做真实资金、撤单、改单、换汇或资金划转。
- 不把 `buying_power` 当作 wallet cash ledger 真源。
- 不要求真实 paper order 必然成交，不把真实 fill 作为默认验收。
- 不改变既有 wallet API DTO、route 路径、envelope 或错误语义。
- 不把真实 Alpaca account id、order id、client order id 或完整响应写入本地数据库、fixture、日志或断言。

## Decisions

### 1. 端到端验证落在测试边界，不进入 runtime adapter

实现 SHALL 优先放在 `apps/api/src/tests/**`。只有当现有 `packages/core/tests/alpaca_paper_adapter_spike.py` 或 broker simulator helper 无法被 API 测试复用时，才允许在 `packages/core/tests/**` 补充测试 helper。补充 helper 仍属于测试边界，不得从 `packages/core/src/**` 导出，也不得作为生产 API 被 runtime 使用。

替代方案是在 `apps/api` 增加 Alpaca sync route。该方案会把 spike 直接变成 runtime 能力，越过当前 OpenSpec 的非目标，因此不采用。

### 2. API route 只读，测试通过本地 wallet service seed 状态

端到端测试 SHALL 在测试进程内创建本地 wallet account、cash balance、paper order 和 paper execution，再通过 `TestClient` 调用既有 `/api/v1/wallet/**` route 读出。API route 不提供写入、同步或 broker 拉取动作。

这样可以验证“wallet service 状态 -> API DTO”的真实链路，同时避免为测试新增对外写 API。

### 3. 外部 smoke 分为只读真实读取与本地入账回放

可选外部 smoke SHALL 只从 Alpaca paper 读取 account、positions 和 orders。真实读取结果只可在内存中转换为脱敏派生的测试输入，例如 `acct_alpaca_e2e_redacted` 或稳定占位 order key；不得把真实 account id、order id、client order id 或完整响应写入本地数据库、fixture、日志或断言。如果需要验证 execution 入账，默认使用 mock / recorded redacted fill 或测试构造的 execution-shaped 数据，除非后续 change 明确允许受控 order submit 和 fill 等待。

这样保留真实 broker shape 的价值，同时避免把真实 paper order 成交作为不稳定验收条件。

### 4. 凭证、URL 和日志沿用 Alpaca spike 约束

实现 SHALL 复用 `ALPACA_PAPER_BASE_URL`、`APCA_API_KEY_ID`、`APCA_API_SECRET_KEY`、`QUANTAGENT_ALPACA_PAPER_SMOKE` 和可新增的端到端专用开关。所有外部测试必须通过 paper-only URL guard，日志、断言、PR 说明不得包含 secret、真实 account id、真实 order id、client order id 或完整第三方响应。外部 smoke 的失败信息必须先脱敏再进入断言或日志。

### 5. 新增开关优先明确端到端语义

为避免已有只读 smoke 被误解为 API 端到端验证，本 change 必须引入独立开关，例如 `QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE=1`。该开关必须同时要求 `QUANTAGENT_ALPACA_PAPER_SMOKE=1`、paper credentials 和 paper URL guard。

### 6. 成功标准分为离线 E2E 与外部 smoke

离线 E2E 是本 change 的必跑验收：它必须证明 Alpaca-shaped fixture 经 wallet ingestion 后能由 `apps/api` wallet routes 读出一致状态。外部 E2E smoke 是可选补充：它只证明当前 credentials 与 Alpaca paper endpoint 可读取，并证明真实响应可被转换为脱敏本地测试输入。外部 smoke 未运行时，不得阻塞本 change 合入，但 PR 必须说明未运行原因。

### 7. 不修改 stable spec，除非实现发现 contract 缺口

如果测试发现 Alpaca 字段无法映射到现有 broker-shaped contract 或 wallet API DTO，默认记录为 gap，并开后续 issue / OpenSpec。不得在本 change 中顺手放宽 `portfolio-wallet-core-v1` 或 API V1 稳定语义。

## Risks / Trade-offs

- [风险] 外部 smoke 受网络、credentials、Alpaca paper account 状态影响。  
  缓解：默认 skip；核心链路用离线确定性测试覆盖，外部结果只作为 PR 说明中的补充验证。

- [风险] 端到端测试被误解为正式 broker 集成能力。  
  缓解：命名、OpenSpec、README 和 PR 说明都明确这是验证 / smoke，不是 runtime adapter 或 plugin。

- [风险] 真实 Alpaca 响应含敏感 identifier。  
  缓解：测试断言只使用存在性、类型和脱敏后的映射结果；不把真实响应落盘。

- [风险] 为测试新增 API 写入口会扩大攻击面和评审范围。  
  缓解：禁止新增 API 写 endpoint；测试内直接 seed 本地 wallet service。

- [风险] 真实 paper order submit 可能造成状态污染。  
  缓解：本 change 默认不提交 paper order；如需验证下单链路，作为单独后续 change 处理。
