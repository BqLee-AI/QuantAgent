## Status

- 当前阶段：实现与校验已完成，待 PR 收口。
- 实现状态：B1-B3、P1-P3、M1、V1、V2 已完成；`openspec` 校验需在仓库根目录执行本机 `openspec` CLI。
- 当前 change：`add-portfolio-wallet-api-v1`。
- 关联 issue：#134。

## Graph Overview

```text
B0 OpenSpec 审核门禁
  -> B1 WalletService 注入与错误映射契约冻结
  -> B2 DTO 字段契约冻结
  -> B3 Router 注册与 endpoint 骨架
  -> P1/P2/P3 并行补测试与文档
  -> M1 契约集成复核
  -> V1/V2 验证
  -> R2 实现 PR 收口
```

关键路径是 B0 -> B1 -> B2 -> B3 -> M1 -> V2。P1/P2/P3 只有在 B3 的公开契约稳定后才可并行。

## Blocking Serial Path

- [x] B0. OpenSpec 审核门禁
  - 输入：issue #134、`proposal.md`、`design.md`、`specs/portfolio-wallet-api-v1/spec.md`、本 `tasks.md`。
  - 输出：OpenSpec 审核结论与可实现的 change artifacts；当前分支已在审核通过后追加 `apps/api` 实现与测试。
  - 写入边界：`openspec/changes/add-portfolio-wallet-api-v1/**`。
  - 依赖：无。
  - 并行性：否。审核通过前不得实现代码；通过后方可追加 runtime 改动。
  - 验证：`openspec validate add-portfolio-wallet-api-v1 --type change --strict --json`。

- [x] B1. 冻结 WalletService 注入与错误映射边界
  - 输入：B0 审核结论、`design.md` 的 session factory 和错误映射规则、现有 `quantagent.api.db`、`quantagent.api.http.errors`、`WalletService` 构造签名。
  - 输出：API 私有 wallet service provider / helper；unknown account、非法 `limit`、paper-only 错误映射为现有 envelope；数据库未配置返回 `ServiceUnavailableError`。
  - 写入边界：`apps/api/src/quantagent/api/**` 中 wallet provider/helper 或 router 私有 helper；不得修改 `packages/core` 领域语义。
  - 依赖：B0。
  - 并行性：否。后续 DTO/router/tests 都依赖这一注入与错误口径。
  - 验证：最小单元或 route 测试能触发 service unavailable、unknown account 和非法 `limit`。

- [x] B2. 冻结 wallet API DTO 与 snapshot 映射
  - 输入：B1 provider 口径、`design.md` DTO 字段表、`WalletService` snapshot dataclass。
  - 输出：`quantagent.api.schemas.wallet` 中的 `WalletAccountResponse`、`WalletCashBalanceResponse`、`WalletPositionResponse`、`WalletLedgerEntryResponse`、`WalletPaperOrderResponse`、`WalletPaperExecutionResponse`；snapshot-to-DTO 映射函数。
  - 写入边界：`apps/api/src/quantagent/api/schemas/**`，必要时 router 私有 mapper；不返回 ORM model 或 core dataclass 作为 response model。
  - 依赖：B1。
  - 并行性：否。公开 response model 是 router 和 OpenAPI 测试的基础。
  - 验证：DTO/mapping 测试覆盖 Decimal、datetime、enum、可选字段和 metadata。

- [x] B3. 实现 protected wallet router 和固定 endpoint
  - 输入：B1 错误映射、B2 DTO/mapping、`STANDARD_API_V1_ROUTER_REGISTRATIONS` protected boundary。
  - 输出：`/api/v1/wallet/accounts/{account_id}` 及其 `cash-balances`、`positions`、`ledger-entries`、`paper-orders`、`paper-executions` 只读 routes；所有 list route 先 `get_trading_account(account_id)`，未知账户不返回空成功列表。
  - 写入边界：`apps/api/src/quantagent/api/routers/v1/**`、必要的 `__init__` / register 更新；不得在 `main.py` 零散 include。
  - 依赖：B2。
  - 并行性：否。多个 endpoint 共享 router/provider/mapping，单 owner 实现更低冲突。
  - 验证：局部 route tests 覆盖 200、401、404、400/422 和 service unavailable。

## Parallel Work After B3

- [x] P1. 补 runtime behavior tests
  - 输入：B3 endpoints、B1 错误映射、B2 DTO。
  - 输出：匿名访问 401、有效 actor 可访问、unknown account、非法 `limit`、service unavailable、unknown account list 不返回空列表的测试。
  - 写入边界：`apps/api/src/tests/**`。
  - 依赖：B3。
  - 并行性：可与 P2/P3 并行；写入同一测试文件时由集成 owner 合并，避免重复 fixture。
  - 验证：相关 unittest 子集或全量 API unittest。

- [x] P2. 补 OpenAPI 与 DTO contract tests
  - 输入：B2 DTO、B3 response_model。
  - 输出：OpenAPI 包含且只包含本 capability 定义的 wallet read routes；每个 route 有 wallet tags 和 `ApiResponse[T]` envelope；无 wallet 写操作或 `WalletFacts` endpoint；Decimal/datetime/enum schema 和 JSON 序列化被固定。
  - 写入边界：`apps/api/src/tests/**`。
  - 依赖：B3。
  - 并行性：可与 P1/P3 并行；不改变 runtime。
  - 验证：OpenAPI 相关 unittest。

- [x] P3. 更新 API README
  - 输入：B3 route 列表、Non-Goals、验证命令。
  - 输出：`apps/api/README.md` 记录 wallet API 是 protected、read-only、paper-only；列出只读 routes 和最小验证命令；明确不支持写操作、`WalletFacts` frontend endpoint 或 live trading。
  - 写入边界：`apps/api/README.md`。
  - 依赖：B3。
  - 并行性：可与 P1/P2 并行；不共享代码写入文件。
  - 验证：人工复核 README 与 OpenAPI route 列表一致。

## Merge / Integration Nodes

- [x] M1. 契约集成复核
  - 输入：B1-B3、P1-P3。
  - 输出：确认 proposal/design/spec/tasks、README、OpenAPI、route 行为和 tests 一致；确认没有新增写操作、facts endpoint、live broker 语义或 core 领域改动。
  - 写入边界：必要时只修正 `apps/api` wallet 相关实现、tests、README 或本 change artifacts。
  - 依赖：B3、P1、P2、P3。
  - 并行性：否。集成点需要单 owner 统一收口。
  - 验证：运行 V2 前的人工 diff review。

## Review Checkpoints

- [x] R1. OpenSpec review gate
  - 条件：B0 完成。
  - 检查：维护者是否明确认可 change artifacts；若未认可，不进入实现。
  - 失败处理：只更新 OpenSpec artifacts，重新运行 V1。

- [x] R2. 实现 PR 收口 gate
  - 条件：M1、V2 完成。
  - 检查：PR 范围只服务 issue #134 / `add-portfolio-wallet-api-v1`；说明依据、改动摘要、验证结果、未验证风险和明确非目标。
  - 失败处理：拆出越界能力或补充新 issue / OpenSpec change。

## Validation Nodes

- [x] V1. OpenSpec validation
  - 触发点：OpenSpec artifacts 创建或修改后。
  - 命令：`openspec validate add-portfolio-wallet-api-v1 --type change --strict --json`。

- [x] V2. API unittest validation
  - 触发点：M1 完成后。
  - 命令：`cd apps/api && uv run python -m unittest discover -s src/tests`。
  - 覆盖：protected boundary、DTO/envelope、错误映射、Decimal/datetime、OpenAPI、敏感信息不泄露。

## Multi-Agent Plan

- 默认不委派。当前 change 的关键写集集中在 `apps/api/src/quantagent/api/**` 和 `apps/api/src/tests/**`，router、DTO、fixtures 与 OpenAPI 测试耦合较高，单 owner 可以减少契约漂移。
- 如果用户明确要求并行，可在 B3 完成后拆 P3 给独立 worker 更新 README；P1/P2 虽可概念并行，但测试 fixture 很可能共享同一文件，建议由同一 owner 合并。
