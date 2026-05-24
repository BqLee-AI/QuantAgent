## 背景

QuantAgent 当前主流程已经围绕 Event、Decision / Policy Gate、Approval、Executor 和 Persistence 建立边界，但账户资产、现金余额、持仓、虚拟订单、虚拟成交、账本和后续实盘边界还没有被收束成明确的后端领域能力。

如果继续只从 executor 或券商插件角度推进，余额计算、持仓更新、多币种折算、虚盘成交、后续券商同步和风控查询会散落到 `apps/api`、executor 插件或策略逻辑里。这样会让真实执行前缺少可审计、可对账、可被 Policy Gate 查询的资产事实层。

本 change 先根据 issue #120 收敛 Portfolio Wallet Core V1 的 OpenSpec 方案：第一版只建设虚盘账户闭环，不连接真实券商账户，不做 live read-only sync，不执行任何实盘写操作。后续 live read-only sync、broker snapshot、reconciliation 和 gated live execution 需要单独 change 收口。

当前实现 PR 已完成 `packages/core` 内的 wallet core 领域对象、持久化、迁移、服务与核心测试。原先在 tasks 中一并列出的 `apps/api` 薄封装、Policy Gate consumer 接入和跨模块集成验证已拆回后续 issue 承接，不再作为本 change 的归档前置范围。

## 改动

- 定义 `packages/core` 下 wallet / portfolio 领域边界，避免将核心余额、持仓、账本、对账和风控查询逻辑写入 FastAPI route。
- 定义 V1 账户模式仅支持 `paper`，并明确 “only 虚盘，不操作实盘”。
- 定义核心模型边界：`TradingAccount`、`CashBalance`、`Position`、`PaperOrder`、`PaperExecution`、`WalletLedgerEntry`、`FxRateSnapshot`。
- 定义多币种虚拟现金余额边界，至少区分 `total`、`available`、`locked`、`unsettled` 和 `currency`。
- 定义现金余额、虚拟持仓、虚拟订单、虚拟成交和 append-only 账本的职责差异。
- 定义 paper simulator / paper executor 与 wallet core 的交互边界：虚盘执行器负责模拟执行，wallet core 负责本地事实层、幂等入库、账本和风控查询。
- 定义 wallet facts 查询边界：由 `packages/core` 暴露可供后续 Decision / Policy Gate consumer 消费的账户模式、现金和持仓事实；最终是否允许任何后续执行动作仍由外层 Decision / Policy Gate 决定。
- 明确真实 secret、完整交易账户信息、私有策略参数和敏感工具参数不得进入仓库、日志或普通 API 响应。
- 明确 `BrokerConnection`、`BrokerSnapshot` 和 `ReconciliationRecord` 只作为后续 live read-only sync phase 的设计输入，不进入 V1 实现范围。
- 明确 `apps/api` 薄封装、Policy Gate consumer 接入和跨模块集成验证不在本次归档范围内，由后续 issue 单独交付。

## 能力

### 新增能力

- `portfolio-wallet-core-v1`: 定义 QuantAgent Portfolio Wallet Core V1 的虚盘账户资产事实层、模型边界、API 边界、Policy Gate 查询边界和非目标。

## 影响

- `packages/core/src/quantagent/core/**`：后续实现 wallet / portfolio 领域模型、repository、service、账本和幂等写入的首选落位。
- `packages/core/alembic/**`：数据库表、迁移和持久化约束的落位；本轮实现已在这里落地首版 wallet core 迁移。
- `apps/api/src/quantagent/api/routers/**` 与 `apps/api/src/quantagent/api/schemas/**`：后续 issue #134 的薄封装落位，不作为本 change 的归档前置条件。
- 现有 Policy Gate / risk check 模块：后续 issue #135 的 facts consumer 接入落位，不作为本 change 的归档前置条件。
- `packages/contracts/**`：V1 OpenSpec 阶段不单独手写 contracts schema；后续实现阶段以 API/OpenAPI 路线同步契约。
- `docs/design/**`：后续需要把 wallet / asset-state 相关的 “only dry-run” 表述收敛为 “only 虚盘，不操作实盘”，但不混入本轮 `packages/core` 实现范围；executor dry-run 作为系统阶段能力的通用表述不在本 change 中误改。
