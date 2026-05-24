## Status

- 当前阶段：当前 PR 作为 `packages/core` 实现 PR 提交，OpenSpec artifacts 与核心实现一并完成 review。
- 范围收窄：本 change 归档前仅覆盖 `packages/core` 领域契约、持久化、迁移、服务、wallet facts 查询和核心测试。
- 后续切片：`apps/api` 薄封装、Policy Gate consumer 接入和跨模块集成验证由 issue #134 / #135 继续推进，不再作为本 change 未完成任务保留。

## Graph Overview

```text
B2 领域契约冻结
  -> B3 持久化和事务边界
  -> B4 入账服务与幂等规则
  -> V1 实现验证
  -> R2 实现 PR 收口
```

当前 change 不再包含 API / Policy Gate 并行切片；后续 issue 依赖本 change 产出的 core 边界继续推进。

## Blocking Serial Path

- [x] B0. OpenSpec review 修订
  - 输入：issue #120、评论中 “only 虚盘，不操作实盘” 约束、本 change 的 proposal/design/spec/tasks、本轮 review findings。
  - 输出：修订后的 OpenSpec artifacts，补齐 simulator -> wallet core 官方路径、首批股票类 spot 范围、可卖持仓 fact、docs/design dry-run 收敛边界。
  - 写入边界：`openspec/changes/add-portfolio-wallet-core-v1/**`。
  - 依赖：无。
  - 并行性：否。OpenSpec artifacts 需要统一收敛。
  - 验证：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`。

- [x] B1. OpenSpec artifacts 审核门禁已在本轮 review 中显式记录
  - 输入：issue #120、评论中 “only 虚盘，不操作实盘” 约束、本 change 的 proposal/design/spec/tasks。
  - 输出：本轮 PR review 中对 OpenSpec artifacts 的主要冲突和 gate 表述已被收口；若后续恢复拆分流程，应由独立 OpenSpec-only PR 承接该门禁。
  - 写入边界：`openspec/changes/add-portfolio-wallet-core-v1/**`。
  - 依赖：B0。
  - 并行性：否。仓库推荐流程下应先完成 artifacts 审核再实现；本次 PR 为合并 review，状态以当前实现 PR 为准。
  - 验证：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`。

- [x] B2. 冻结 wallet core 领域契约
  - 输入：`design.md` 的目标、非目标、事实层/证据层/投影层决策；`spec.md` 的 requirement。
  - 输出：领域对象和服务入口草案，覆盖 `TradingAccount`、`CashBalance`、`Position`、`PaperOrder`、`PaperExecution`、`WalletLedgerEntry`、`FxRateSnapshot`。
  - 写入边界：`packages/core/src/quantagent/core/**` 中 wallet / portfolio 模块；必要的 core package export。
  - 依赖：B1。
  - 并行性：否。后续持久化、API 和测试都依赖这些契约。
  - 验证：core 单元测试能导入领域对象；类型、枚举和值对象不依赖 `apps/api`、`apps/web` 或具体插件实现。

- [x] B3. 定义持久化、迁移和事务边界
  - 输入：B2 领域契约；`packages/core` Alembic 规则；spec 中 append-only ledger、snapshot 分离、Decimal/Numeric 和幂等来源键要求。
  - 输出：ORM model、迁移和 repository 边界；账户范围内 paper execution 幂等唯一约束；ledger 与 snapshot 同事务写入约束。
  - 写入边界：`packages/core/src/quantagent/core/db/**`、`packages/core/alembic/**`、`packages/core/tests/**`。
  - 依赖：B2。
  - 并行性：否。数据模型和迁移是后续 service/API 的基础。
  - 验证：迁移配置可解析；repository 测试覆盖 Decimal/Numeric、append-only ledger、snapshot 分离和幂等唯一约束。

- [x] B4. 实现 wallet 入账和查询服务
  - 输入：B3 repository / transaction 边界；spec 中 paper execution、ledger、facts query、人工调整和脱敏要求。
  - 输出：core wallet service，支持虚盘账户初始化、虚拟入金/出金/人工调整、paper execution 幂等入账、cash/position/ledger 查询、Policy Gate facts 查询。
  - 写入边界：`packages/core/src/quantagent/core/**` wallet / portfolio service；`packages/core/tests/**` service 测试。
  - 依赖：B3。
  - 并行性：部分可并行。入账服务和只读查询可以拆开，但必须共用 B3 契约，并在 M1 前合并。
  - 验证：单账户 paper wallet 测试覆盖余额、持仓、虚拟订单、虚拟成交、账本写入和重复 execution 不重复入账。

## Review Checkpoints

- [x] R1. OpenSpec review gate
  - 条件：B1 完成。
  - 检查：proposal/design/spec/tasks 是否仍一致；维护者是否明确同意 V1 范围。
  - 失败处理：只更新 OpenSpec artifacts，重新验证并等待确认。

- [x] R2. 实现 PR 收口 gate
  - 条件：B4、V1、V4 完成。
  - 检查：PR 范围已收窄到 `packages/core` 实际交付；后续 API / consumer / integration 事项已回收到独立 issue；说明依据、改动摘要、验证结果和未纳入本 change 的后续风险。
  - 失败处理：继续收窄 OpenSpec artifacts，或把未完成外围事项拆回后续 issue / change。

## Validation Nodes

- [x] V0. OpenSpec validation
  - 命令：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`
  - 当前结果：已通过。

- [x] V1. Core wallet validation
  - 触发点：B4 完成后。
  - 覆盖：单账户 paper wallet、余额、持仓、虚拟订单、虚拟成交、账本写入、多币种 cash balance、Decimal/Numeric、重复 execution 幂等、人工调整不绕过 ledger。
  - 推荐命令：在实现阶段按 `packages/core` 现有测试入口运行最小相关 Python 测试。

- [x] V4. Final OpenSpec validation
  - 触发点：实现期间如果修改本 change artifacts。
  - 命令：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`

## Follow-up

- issue #134：承接 `apps/api` 的 wallet DTO / route 薄封装与 API 边界验证。
- issue #135：承接 Policy Gate / risk check 对 wallet facts 的 consumer 接入与集成验证。
- 如后续需要 live read-only sync、broker snapshot、reconciliation 或 gated live execution，必须单开新的 OpenSpec change。
