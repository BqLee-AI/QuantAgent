## Context

issue #134 承接已归档的 `add-portfolio-wallet-core-v1` 后续切片。当前 stable spec 已经冻结 `packages/core` 的 paper-only wallet core、snapshot、ledger、paper order、paper execution 和 wallet facts 查询边界；但 `apps/api` 还没有正式 HTTP 资源让前端、调试和集成验证通过统一 envelope、鉴权和 OpenAPI 契约访问这些只读事实。

`apps/api` 的本地约束要求 route 保持薄层：API 只处理 HTTP 参数、DTO、状态码、响应 envelope、异常映射和依赖注入，核心余额、持仓、账本、入账和风险计算必须留在 `packages/core`。现有 API v1 route 通过 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 统一声明 public/protected 边界；业务 route 默认 protected。

本 change 先定义 API 文档与实现口径，再在 OpenSpec 审核通过后落地 `apps/api` runtime、测试和 README。当前 PR 不是 OpenSpec-only PR；它已经同时包含：

- `openspec/changes/add-portfolio-wallet-api-v1/**` 的 proposal/design/spec/tasks
- `apps/api/src/quantagent/api/**` 的 wallet runtime 实现
- `apps/api/src/tests/**` 的 route / OpenAPI / error mapping tests
- `apps/api/README.md` 的交付说明

review 时应同时检查文档契约与对应实现是否一致，而不是把实现误判为越过 review gate 的额外范围。

## Goals / Non-Goals

**Goals:**

- 暴露 Portfolio Wallet Core V1 的第一组受保护、只读、paper-only HTTP 查询资源。
- 为 account、cash balance、position、ledger entry、paper order 和 paper execution 定义 API DTO 映射边界。
- 保持 API 响应使用 `ApiResponse[T]` envelope，并在 OpenAPI 中体现 envelope、tags 和 DTO。
- 将 core service 的 unknown account、非法参数和 wallet 边界错误映射为统一 API 错误 envelope。
- 用 tests 证明 protected、DTO、脱敏、Decimal/datetime 序列化、OpenAPI 和 paper-only 文案边界。

**Non-Goals:**

- 不开放账户创建、现金调整、paper order 写入、paper execution 写入或 FX snapshot 写入 API。
- 不暴露 `WalletFacts` 前端 endpoint；facts consumer 由 Policy Gate / risk check 后续 issue 承接。
- 不实现余额、持仓、账本、入账、估值、风控或对账计算。
- 不新增真实券商连接、真实账户同步、真实下单、撤单、改单、换汇、资金划转或 live trading API。
- 不新增 `packages/contracts` 手写 schema、generated client、TypeScript types 或 Zod schema。
- 不把 ORM model、core dataclass、secret、完整账户号、真实交易密钥、私有策略参数或本地 runtime 路径返回给前端。

## Decisions

### 1. 新建 `portfolio-wallet-api-v1` 能力，不修改 core stable spec

issue #134 原文提到复用 `add-portfolio-wallet-core-v1`，但该 change 在当前仓库已经归档，且 stable spec 明确 API 薄封装属于后续能力。因此本轮使用新的 active change 描述 API behavior，依赖但不改写 `portfolio-wallet-core-v1`。

替代方案是直接修改 stable spec。该方案会绕过 active change review 链路，也容易把 core 已归档 requirement 和 API 后续 capability 混在一起，因此不采用。

### 2. API route 通过 protected registration boundary 接入

Wallet API route SHALL 作为标准 API v1 protected router 注册到 `register_api_v1_routes`。它不加入 public allowlist，不依赖 route-level ad hoc 鉴权代替统一 registration boundary。

替代方案是在 `main.py` 直接 `include_router(...)` 或在各 route 上零散加鉴权依赖。该方案会破坏 public/protected 真源，不采用。

### 3. `WalletService` 注入使用 app-level session factory，不使用请求级 Session 构造服务

当前 `WalletService` 构造参数是 `sessionmaker[Session]`，并由 service 方法自己创建事务或只读 session。后续实现 SHALL 从 `request.app.state.db_session_factory` 获取 session factory 来构造或复用 `WalletService`；当 session factory 缺失时，复用现有 `ServiceUnavailableError("Database not configured")` 或 `ServiceUnavailableError("Database not ready")` 语义。

Route SHALL NOT 使用 `get_db_session` 产出的请求级 `Session` 去构造 `WalletService`，也不在 route 内创建 engine、sessionmaker 或直接管理 wallet transaction。若实现希望缓存 service，可以挂在 `app.state.wallet_service`，但必须确保它只包裹当前 app 的 session factory，且测试可替换。

替代方案是把请求级 `Session` 注入 route 后直接查 repository。该方案会把 API route 变厚，绕开 core service 的事务和 paper-only 校验，不采用。

### 4. DTO 是 API 契约，不直接复用 ORM 或 core dataclass

API response DTO SHALL 放在 `quantagent.api.schemas.wallet`。DTO 字段从 `WalletService` 返回的 snapshot 映射，允许沿用 snapshot 的稳定语义，但不能直接把 ORM model、SQLAlchemy model 或 core dataclass 作为 FastAPI response model 返回。

公开 DTO 使用以下字段名，避免实现阶段自由发挥：

| DTO | 字段 |
| --- | --- |
| `WalletAccountResponse` | `account_id`, `name`, `mode`, `base_currency`, `created_at` |
| `WalletCashBalanceResponse` | `account_id`, `currency`, `total`, `available`, `locked`, `unsettled`, `updated_at` |
| `WalletPositionResponse` | `account_id`, `instrument`, `market`, `side`, `quantity`, `sellable_quantity`, `average_cost`, `market_value`, `unrealized_pnl`, `currency`, `updated_at` |
| `WalletLedgerEntryResponse` | `entry_id`, `account_id`, `entry_type`, `currency`, `amount`, `source_type`, `source_ref`, `occurred_at`, `order_id`, `execution_id`, `metadata`, `created_at` |
| `WalletPaperOrderResponse` | `order_id`, `account_id`, `client_order_id`, `instrument`, `market`, `side`, `order_type`, `quantity`, `limit_price`, `currency`, `status`, `requested_at`, `completed_at` |
| `WalletPaperExecutionResponse` | `execution_id`, `account_id`, `order_id`, `idempotency_key`, `instrument`, `market`, `side`, `quantity`, `price`, `gross_amount`, `currency`, `fee_amount`, `fee_currency`, `executed_at`, `created_at` |

Decimal 字段 SHALL 保持 Pydantic 默认 JSON 序列化行为，并由测试固定当前输出形态；不要在本 change 中引入自定义金额字符串格式、rounding policy 或前端展示单位。Datetime 字段 SHALL 使用 timezone-aware ISO 8601 JSON 表达。

替代方案是让 route 直接返回 core snapshot。该方案会把内部 dataclass 变成公开 HTTP 契约，后续 core 重构会影响 API 兼容性，也不利于脱敏和字段命名审查，因此不采用。

### 5. 最小资源路径只覆盖只读查询，且每个 account-scoped 列表先校验账户存在

后续实现 SHALL 采用 `/api/v1/wallet/accounts/{account_id}` 作为账户资源根，并在其下暴露只读子资源：

| Route | Core service 调用 | 成功 data 类型 |
| --- | --- | --- |
| `GET /api/v1/wallet/accounts/{account_id}` | `get_trading_account(account_id)` | `WalletAccountResponse` |
| `GET /api/v1/wallet/accounts/{account_id}/cash-balances` | `get_trading_account(account_id)` then `list_cash_balances(account_id)` | `list[WalletCashBalanceResponse]` |
| `GET /api/v1/wallet/accounts/{account_id}/positions` | `get_trading_account(account_id)` then `list_positions(account_id)` | `list[WalletPositionResponse]` |
| `GET /api/v1/wallet/accounts/{account_id}/ledger-entries` | `get_trading_account(account_id)` then `list_ledger_entries(account_id, limit=limit)` | `list[WalletLedgerEntryResponse]` |
| `GET /api/v1/wallet/accounts/{account_id}/paper-orders` | `get_trading_account(account_id)` then `list_paper_orders(account_id)` | `list[WalletPaperOrderResponse]` |
| `GET /api/v1/wallet/accounts/{account_id}/paper-executions` | `get_trading_account(account_id)` then `list_paper_executions(account_id)` | `list[WalletPaperExecutionResponse]` |

所有 account-scoped list route MUST 先调用 `get_trading_account(account_id)` 校验账户存在。`WalletService` 的 list 方法当前可对未知账户返回空列表；API 不得把未知账户误报为空资源。

Ledger entries 支持可选 `limit: int | None = None`。当提供 `limit` 时，它必须是正整数；非法值走 422 validation envelope 或 400 bad request envelope，二者均可接受，但测试必须固定实现选择。其他过滤、分页、排序和 search 不进入本轮。

替代方案是把 wallet facts、写操作或 action endpoint 一并放入 wallet router。该方案会扩大权限、CSRF、审计和 Policy Gate 设计范围，不采用。

### 6. 错误映射在 API 层集中表达，规则固定

Wallet route SHALL 使用一个 API 私有 helper 映射预期错误，避免每个 route 自己解释 `ValueError`。实现阶段的固定映射规则如下：

- `get_trading_account(account_id)` 返回 `None`：raise `NotFoundError("Wallet account not found", details={"account_id": account_id})`。
- `ValueError` message 以 `Unknown trading account:` 开头：raise `NotFoundError("Wallet account not found", details={"account_id": account_id})`。
- `ValueError` message 等于或包含 `limit must be greater than zero.`：raise `BadRequestError("Invalid wallet query", details={"field": "limit"})`，除非该错误已由 FastAPI 参数校验拦截为 422。
- `ValueError` message 等于 `Portfolio Wallet Core V1 only supports paper accounts.`：raise `BadRequestError("Wallet API only supports paper accounts")`。
- 其他 `ValueError`：raise `BadRequestError("Invalid wallet request")`，details 只放安全字段名，不放原始 payload、SQL、traceback 或 secret。

客户端错误文案不得暴露 DB 连接串、traceback、secret、完整账户号或内部 SQLAlchemy 细节。未预期异常继续交给全局 exception handler。

替代方案是让 `ValueError` 直接走 500 handler。该方案会让正常客户端错误变成 internal error，也不满足 issue #134 的错误映射验收，不采用。

### 7. Ledger metadata 保守透出，不做敏感值推断

当前 core ledger metadata 来源主要是受控 note 或交易摘要。API DTO 可以保留 `metadata: dict[str, str]`，但 route 不得添加新的 metadata key，也不得把 request headers、cookie、session、database URL、runtime path、broker credential、完整真实账号或私有策略参数写入 metadata。

如果后续发现 core metadata 可能包含敏感信息，应在 core 或新 change 中定义 typed metadata / allowlist；本 change 不在 API 层用临时字符串规则猜测和改写历史 metadata。

### 8. paper-only 语义必须进入路径、schema、文案和测试

Wallet API SHALL 明确表达它查询的是 Portfolio Wallet Core V1 的 paper account 资源。DTO 中 account mode 只能展示 `paper`；paper order 和 paper execution 的命名不得被泛化成真实 broker order / execution。错误消息和 README 不应暗示支持 live broker action。

替代方案是使用泛化交易账户 API 命名。该方案容易让 reviewer 或前端误解为真实账户同步或真实交易 API 已完成，不采用。

### 9. OpenAPI 是本轮契约来源

本轮 SHALL 通过 FastAPI `response_model=ApiResponse[T]` 和 tests 校验 OpenAPI schema，不新增 `packages/contracts` 手写 schema 或生成链路。若后续前端需要 generated client，再由单独 issue 收口 generation source、命令和消费者。

## Implementation Boundaries

- Canonical asset: `packages/core` 的 wallet service、snapshot 和 stable `portfolio-wallet-core-v1` spec。
- API contract: `quantagent.api.schemas.wallet` DTO、wallet router 的 `response_model` 和 `/openapi.json`。
- Derived layer: README、测试 fixture、OpenAPI schema inspection helper、前端后续 generated client。
- Forbidden bypass: route 直接创建 engine/sessionmaker、直接查 wallet ORM、直接返回 ORM/core dataclass、在 API 层计算资产事实、把 `WalletFacts` 暴露为前端 endpoint、添加 wallet 写操作或真实 broker action。

## Risks / Trade-offs

- [Risk] core service 目前用 `ValueError` 表达多类错误，API 映射可能依赖 message pattern。 -> Mitigation: 本轮固定少量已知 message 的映射规则，并在 tests 中覆盖；后续若 core 增加 typed domain errors，再收敛映射。
- [Risk] 未实现分页会让 ledger/order/execution 列表在长期数据下变大。 -> Mitigation: 本轮只允许最小 `limit`；完整分页、游标和排序作为后续 API 扩展。
- [Risk] account_id 可能包含完整账户号语义。 -> Mitigation: V1 core 账户是 paper account id；API 测试和 DTO 审查必须证明不返回真实 broker account、secret 或 runtime path。若后续引入真实账户，需新 change 定义脱敏 ID。
- [Risk] API fields 与 core snapshot fields 可能漂移。 -> Mitigation: DTO 映射测试以 `WalletService` snapshot 语义为输入，OpenAPI contract tests 固定公开字段。
- [Risk] reviewer 可能把当前分支误读为仍是 OpenSpec-only。 -> Mitigation: proposal、tasks 和 PR 描述显式说明本分支已包含通过 OpenSpec 审核后的 API 实现与验证。
