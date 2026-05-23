## Status

- 当前阶段：OpenSpec-only 文档评审。
- 实现状态：Blocked，必须先提交 OpenSpec-only PR，并等维护者明确评论“没问题”或批准后，才能进入实现 PR。
- 当前 change 不允许写实现代码、迁移、依赖升级、生成 contracts 或无关 docs。

## Graph Overview

关键路径：

```text
B0 OpenSpec review 修订
  -> B1 OpenSpec 审核
  -> B2 领域契约冻结
  -> B3 持久化和事务边界
  -> B4 入账服务与幂等规则
  -> M1 API / Policy Gate 集成边界
  -> V1 实现验证
  -> R2 实现 PR 准备
```

OpenSpec-only PR 通过后的实现关键路径：

```text
B2 领域契约冻结
  -> B3 持久化和事务边界
  -> B4 入账服务与幂等规则
  -> M1 API / Policy Gate 集成边界
  -> V1 实现验证
  -> R2 实现 PR 准备
```

可并行点：

- `B3` 完成且 `B4` service interface 草案稳定后，core service、API DTO/route、测试 fixture 可以并行推进，但必须在 `M1` 汇合。
- `docs/design` 中 wallet / asset-state 相关 “only dry-run” 表述收敛可以作为独立后续任务处理，不阻塞 core 实现，但不能混入 OpenSpec-only PR；executor dry-run 作为系统阶段能力的通用表述不在本 change 中误改。

## Blocking Serial Path

- [ ] B0. OpenSpec review 修订
  - 输入：issue #120、评论中 “only 虚盘，不操作实盘” 约束、本 change 的 proposal/design/spec/tasks、本轮 review findings。
  - 输出：修订后的 OpenSpec artifacts，补齐 simulator -> wallet core 官方路径、首批股票类 spot 范围、可卖持仓 fact、docs/design dry-run 收敛边界。
  - 写入边界：`openspec/changes/add-portfolio-wallet-core-v1/**`。
  - 依赖：无。
  - 并行性：否。OpenSpec artifacts 需要统一收敛。
  - 验证：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`。

- [ ] B1. OpenSpec-only PR 审核
  - 输入：issue #120、评论中 “only 虚盘，不操作实盘” 约束、本 change 的 proposal/design/spec/tasks。
  - 输出：维护者在 OpenSpec-only PR 下明确评论“没问题”或批准。
  - 写入边界：`openspec/changes/add-portfolio-wallet-core-v1/**`。
  - 依赖：B0。
  - 并行性：否。未通过审核前不得实现代码。
  - 验证：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`。

- [ ] B2. 冻结 wallet core 领域契约
  - 输入：`design.md` 的目标、非目标、事实层/证据层/投影层决策；`spec.md` 的 requirement。
  - 输出：领域对象和服务入口草案，覆盖 `TradingAccount`、`CashBalance`、`Position`、`PaperOrder`、`PaperExecution`、`WalletLedgerEntry`、`FxRateSnapshot`。
  - 写入边界：`packages/core/src/quantagent/core/**` 中 wallet / portfolio 模块；必要的 core package export。
  - 依赖：B1。
  - 并行性：否。后续持久化、API 和测试都依赖这些契约。
  - 验证：core 单元测试能导入领域对象；类型、枚举和值对象不依赖 `apps/api`、`apps/web` 或具体插件实现。

- [ ] B3. 定义持久化、迁移和事务边界
  - 输入：B2 领域契约；`packages/core` Alembic 规则；spec 中 append-only ledger、snapshot 分离、Decimal/Numeric 和幂等来源键要求。
  - 输出：ORM model、迁移和 repository 边界；账户范围内 paper execution 幂等唯一约束；ledger 与 snapshot 同事务写入约束。
  - 写入边界：`packages/core/src/quantagent/core/db/**`、`packages/core/alembic/**`、`packages/core/tests/**`。
  - 依赖：B2。
  - 并行性：否。数据模型和迁移是后续 service/API 的基础。
  - 验证：迁移配置可解析；repository 测试覆盖 Decimal/Numeric、append-only ledger、snapshot 分离和幂等唯一约束。

- [ ] B4. 实现 wallet 入账和查询服务
  - 输入：B3 repository / transaction 边界；spec 中 paper execution、ledger、facts query、人工调整和脱敏要求。
  - 输出：core wallet service，支持虚盘账户初始化、虚拟入金/出金/人工调整、paper execution 幂等入账、cash/position/ledger 查询、Policy Gate facts 查询。
  - 写入边界：`packages/core/src/quantagent/core/**` wallet / portfolio service；`packages/core/tests/**` service 测试。
  - 依赖：B3。
  - 并行性：部分可并行。入账服务和只读查询可以拆开，但必须共用 B3 契约，并在 M1 前合并。
  - 验证：单账户 paper wallet 测试覆盖余额、持仓、虚拟订单、虚拟成交、账本写入和重复 execution 不重复入账。

## Parallel Work After B3 And B4 Interface Draft

- [ ] P1. API DTO 与 route 薄封装
  - 输入：B2 领域契约、B3 repository 边界、B4 service 接口草案。
  - 输出：账户、余额、持仓、账本、paper orders、paper executions 的 API DTO 和 route；统一 envelope；错误映射。
  - 写入边界：`apps/api/src/quantagent/api/routers/**`、`apps/api/src/quantagent/api/schemas/**`、`apps/api/src/tests/**`。
  - 依赖：B3，且不得先于 B4 service 接口稳定。
  - 并行性：是。可与 B4 的 core service 细节并行，但不能自行实现资产计算。
  - 验证：API 测试证明 route 调用 core service、返回 DTO、不直接返回 ORM model、不暴露 secret 或完整账户号。

- [ ] P2. Policy Gate facts 消费接口对接
  - 输入：B4 wallet facts 查询接口；现有 Decision / Policy Gate 边界。
  - 输出：Policy Gate 或 risk check 可查询虚盘账户 mode、available cash、locked cash、unsettled cash、position quantity、sellable position、single-instrument exposure 和 paper execution permission。
  - 写入边界：现有 Policy Gate / risk check 所在模块；如尚无实现，则只在 core 中暴露 facts port，不新增完整 Policy Gate。
  - 依赖：B4 facts interface。
  - 并行性：是。只要 facts interface 稳定，可与 API route 并行。
  - 验证：测试证明 Policy Gate 输入来自 wallet facts，wallet core 不自行放行真实或高风险动作。

- [ ] P3. 实现阶段测试 fixture 与验收样例
  - 输入：B2-B4 契约；spec 中 V1 场景。
  - 输出：最小 paper account fixture、多币种 cash fixture、重复 execution fixture、脱敏响应 fixture。
  - 写入边界：`packages/core/tests/**`、`apps/api/src/tests/**`。
  - 依赖：B3。
  - 并行性：是。fixture 可与 service/API 实现并行维护，但断言必须在 M1 后对齐最终契约。
  - 验证：fixture 被 core/API 测试复用，避免只存在未使用样例。

## Merge / Integration Nodes

- [ ] M1. Core/API/Policy Gate 契约汇合
  - 输入：B4、P1、P2、P3。
  - 输出：一致的 service 接口、DTO 字段、错误结构、脱敏规则和测试断言；确认 API 资源只表示虚盘，不暗示真实 broker action。
  - 写入边界：`packages/core/**`、`apps/api/**` 的接口对齐小改；不得新增 unrelated refactor。
  - 依赖：B4、P1、P2、P3。
  - 并行性：否。所有切片必须在此汇合。
  - 验证：core tests + API tests；人工检查 API DTO 不暴露 ORM、secret、完整账户号或真实 broker action。

- [ ] M2. 后续 phase 边界复核
  - 输入：design/spec 的非目标和 deferred boundary。
  - 输出：确认实现未包含 `BrokerConnection`、`BrokerSnapshot`、`ReconciliationRecord`、live read-only sync、真实下单、真实换汇、复杂风控配置或 hand-written contracts schema。
  - 写入边界：无实现写入；如发现越界，只回退本 change 相关实现或开后续 issue/change。
  - 依赖：M1。
  - 并行性：否。作为实现收口审查。
  - 验证：git diff review。

## Review Checkpoints

- [ ] R1. OpenSpec review gate
  - 条件：B1 完成。
  - 检查：proposal/design/spec/tasks 是否仍一致；维护者是否明确同意 V1 范围。
  - 失败处理：只更新 OpenSpec artifacts，重新验证并等待确认。

- [ ] R2. 实现 PR 准备 gate
  - 条件：M1、M2、V1 完成。
  - 检查：PR 只绑定 `add-portfolio-wallet-core-v1`；说明依据、改动摘要、验证结果、未验证风险和后续 docs/design 表述收敛。
  - 失败处理：拆分越界实现或补后续 issue/change。

## Validation Nodes

- [x] V0. OpenSpec validation
  - 命令：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`
  - 当前结果：已通过。

- [ ] V1. Core wallet validation
  - 触发点：B4 完成后。
  - 覆盖：单账户 paper wallet、余额、持仓、虚拟订单、虚拟成交、账本写入、多币种 cash balance、Decimal/Numeric、重复 execution 幂等、人工调整不绕过 ledger。
  - 推荐命令：在实现阶段按 `packages/core` 现有测试入口运行最小相关 Python 测试。

- [ ] V2. API boundary validation
  - 触发点：P1 与 M1 完成后。
  - 覆盖：API envelope、DTO、错误映射、ORM 不直出、敏感字段脱敏、paper-only endpoint 不暗示真实 broker action。
  - 推荐命令：在实现阶段按 `apps/api` 现有测试入口运行相关 API 测试。

- [ ] V3. Integration validation
  - 触发点：M1 完成后。
  - 覆盖：API route 调 core service；Policy Gate / risk check 消费 wallet facts；wallet core 不自行放行真实或高风险动作。
  - 推荐命令：core/API 相关测试组合，必要时补最小集成测试。

- [ ] V4. Final OpenSpec validation
  - 触发点：实现期间如果修改本 change artifacts。
  - 命令：`openspec validate add-portfolio-wallet-core-v1 --type change --strict --json`

## Multi-Agent Plan

- OpenSpec-only 阶段不建议委派：写入范围集中在同一个 change artifacts，拆分收益低，冲突风险高。
- 实现阶段可在 B3 完成后并行：
  - Core service owner：负责 B4，写 `packages/core/**`。
  - API owner：负责 P1，写 `apps/api/**`，不得实现资产计算。
  - Test owner：负责 P3，写测试 fixture 和断言。
- 集成 owner 必须统一负责 M1，避免 service、DTO、测试和 Policy Gate facts drift。
