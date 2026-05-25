## ADDED Requirements

### Requirement: Wallet API V1 是受保护的只读 paper account 边界

QuantAgent SHALL expose Portfolio Wallet API V1 as protected, read-only HTTP resources for paper accounts backed by Portfolio Wallet Core V1.

#### Scenario: 匿名访问 wallet API 被拒绝
- **WHEN** an anonymous client requests any `/api/v1/wallet/**` route
- **THEN** the API returns the existing unauthorized envelope
- **AND** the route is not part of the API v1 public allowlist

#### Scenario: 有效 actor 可以查询 paper wallet resources
- **WHEN** an authenticated client requests a supported wallet read route
- **THEN** the API evaluates the request through the API v1 protected registration boundary
- **AND** the route returns an `ApiResponse` envelope when the wallet service query succeeds

#### Scenario: Wallet API 不暴露写操作
- **WHEN** Portfolio Wallet API V1 is implemented
- **THEN** it exposes no route for account creation, cash adjustment, paper order creation, paper execution ingestion, FX snapshot creation or wallet facts frontend query
- **AND** side-effecting wallet operations remain outside this API V1 capability

### Requirement: Wallet API V1 暴露固定账户资源查询

Portfolio Wallet API V1 SHALL expose only the account-scoped read resources defined by this requirement.

#### Scenario: 查询账户快照
- **WHEN** an authenticated client requests `GET /api/v1/wallet/accounts/{account_id}`
- **THEN** the API calls `WalletService.get_trading_account(account_id)`
- **AND** the API returns `ApiResponse[WalletAccountResponse]`
- **AND** the response data includes `account_id`, `name`, `mode`, `base_currency` and `created_at`
- **AND** `mode` is represented as `paper`

#### Scenario: 查询现金余额列表
- **WHEN** an authenticated client requests `GET /api/v1/wallet/accounts/{account_id}/cash-balances`
- **THEN** the API first verifies the account with `WalletService.get_trading_account(account_id)`
- **AND** the API calls `WalletService.list_cash_balances(account_id)`
- **AND** the API returns `ApiResponse[list[WalletCashBalanceResponse]]`
- **AND** each item includes `account_id`, `currency`, `total`, `available`, `locked`, `unsettled` and `updated_at`

#### Scenario: 查询持仓列表
- **WHEN** an authenticated client requests `GET /api/v1/wallet/accounts/{account_id}/positions`
- **THEN** the API first verifies the account with `WalletService.get_trading_account(account_id)`
- **AND** the API calls `WalletService.list_positions(account_id)`
- **AND** the API returns `ApiResponse[list[WalletPositionResponse]]`
- **AND** each item includes `account_id`, `instrument`, `market`, `side`, `quantity`, `sellable_quantity`, `average_cost`, `market_value`, `unrealized_pnl`, `currency` and `updated_at`

#### Scenario: 查询账本历史
- **WHEN** an authenticated client requests `GET /api/v1/wallet/accounts/{account_id}/ledger-entries`
- **THEN** the API first verifies the account with `WalletService.get_trading_account(account_id)`
- **AND** the API calls `WalletService.list_ledger_entries(account_id, limit=limit)`
- **AND** the API returns `ApiResponse[list[WalletLedgerEntryResponse]]`
- **AND** each item includes `entry_id`, `account_id`, `entry_type`, `currency`, `amount`, `source_type`, `source_ref`, `occurred_at`, `order_id`, `execution_id`, `metadata` and `created_at`

#### Scenario: 查询虚拟订单列表
- **WHEN** an authenticated client requests `GET /api/v1/wallet/accounts/{account_id}/paper-orders`
- **THEN** the API first verifies the account with `WalletService.get_trading_account(account_id)`
- **AND** the API calls `WalletService.list_paper_orders(account_id)`
- **AND** the API returns `ApiResponse[list[WalletPaperOrderResponse]]`
- **AND** each item uses paper order naming and does not imply a live broker order

#### Scenario: 查询虚拟成交列表
- **WHEN** an authenticated client requests `GET /api/v1/wallet/accounts/{account_id}/paper-executions`
- **THEN** the API first verifies the account with `WalletService.get_trading_account(account_id)`
- **AND** the API calls `WalletService.list_paper_executions(account_id)`
- **AND** the API returns `ApiResponse[list[WalletPaperExecutionResponse]]`
- **AND** each item uses paper execution naming and does not imply a live broker execution

#### Scenario: 未知账户列表查询不返回空列表
- **WHEN** an authenticated client requests any account-scoped wallet list route for an unknown account id
- **THEN** the API returns a not found envelope
- **AND** it does not return an empty success list for the unknown account

### Requirement: Wallet API DTO 独立于 ORM 和 core 内部对象

Portfolio Wallet API V1 SHALL define transport DTOs that are independent of ORM models and core dataclasses.

#### Scenario: Route 返回 API DTO
- **WHEN** a wallet route returns successful data
- **THEN** the FastAPI route declares `response_model=ApiResponse[T]`
- **AND** `T` is an API schema from `quantagent.api.schemas.wallet`
- **AND** the route does not return a SQLAlchemy ORM model as the public response object
- **AND** the route does not use a core dataclass as the public response model

#### Scenario: Core snapshot 映射为公开 DTO
- **WHEN** the route receives a snapshot from `WalletService`
- **THEN** the route maps it into an API DTO before returning
- **AND** the mapping preserves the field names defined in `design.md`
- **AND** the mapping may omit only fields that are not listed in the API DTO contract

#### Scenario: 数值和时间字段可序列化
- **WHEN** wallet DTOs contain Decimal or datetime values
- **THEN** the API serializes them through Pydantic/FastAPI into JSON-compatible OpenAPI-backed responses
- **AND** tests cover Decimal and timezone-aware datetime serialization

### Requirement: Wallet API 调用 core service 而不复制领域逻辑

Portfolio Wallet API V1 SHALL delegate wallet facts storage and calculations to `packages/core`.

#### Scenario: Route 使用 session factory 构造 WalletService
- **WHEN** a wallet read route needs account, cash, position, ledger, paper order or paper execution data
- **THEN** it obtains the app-level database session factory from `request.app.state.db_session_factory`
- **AND** it calls `WalletService` or an explicit API injection boundary backed by that session factory
- **AND** it does not pass a request-scoped `Session` object into `WalletService`

#### Scenario: Route 不绕过 core service
- **WHEN** the API returns wallet data
- **THEN** it does not directly create database engines in the route
- **AND** it does not directly query wallet ORM models from the route
- **AND** it does not recompute balances, positions, ledger effects, fees, average cost, market value or risk facts

#### Scenario: 数据库未配置时返回 service unavailable
- **WHEN** a wallet route is requested while the app has no database session factory
- **THEN** the API returns the existing service unavailable envelope
- **AND** the response does not expose database URLs, credentials or traceback

### Requirement: Wallet API 错误响应使用统一 envelope

Portfolio Wallet API V1 SHALL map expected wallet query failures to the existing API error envelope.

#### Scenario: 未知账户返回 not found envelope
- **WHEN** `WalletService.get_trading_account(account_id)` returns no account
- **THEN** the API returns a not found error envelope
- **AND** the response includes `error.request_id`
- **AND** the response details include only the requested `account_id`
- **AND** the response does not expose traceback, SQL, connection strings or secrets

#### Scenario: Core unknown account error 返回 not found envelope
- **WHEN** wallet core raises a `ValueError` whose message starts with `Unknown trading account:`
- **THEN** the API maps it to a not found error envelope
- **AND** the response does not expose the raw exception type or traceback

#### Scenario: 非法 limit 返回客户端错误
- **WHEN** an authenticated client sends a non-positive ledger `limit`
- **THEN** the API returns the existing validation or bad request envelope
- **AND** tests lock the chosen status and envelope shape
- **AND** the response does not expose internal wallet service implementation details

#### Scenario: Paper-only 边界错误返回客户端错误
- **WHEN** wallet core reports `Portfolio Wallet Core V1 only supports paper accounts.`
- **THEN** the API maps it to a controlled client error envelope
- **AND** the message preserves paper-only semantics without exposing internal state

### Requirement: Wallet API 不泄露敏感信息

Portfolio Wallet API V1 SHALL avoid exposing secrets, real broker information and local runtime details.

#### Scenario: Response 不返回敏感字段
- **WHEN** wallet API returns account, balance, position, ledger, order or execution data
- **THEN** the response does not include secrets, tokens, real broker credentials, private strategy parameters, local runtime paths or database connection details
- **AND** the response does not include full real broker account numbers

#### Scenario: Ledger metadata 公开前受控
- **WHEN** wallet ledger entries contain metadata
- **THEN** the API does not add request headers, cookies, session data, database URLs, runtime paths, broker credentials, full real account numbers or private strategy parameters to metadata
- **AND** tests cover that sensitive metadata keys are not introduced by the API mapping

### Requirement: Wallet API OpenAPI 契约可审核

Portfolio Wallet API V1 SHALL be visible in development OpenAPI with stable envelope and tags.

#### Scenario: Wallet routes appear in OpenAPI
- **WHEN** tests read development `/openapi.json`
- **THEN** the schema contains exactly the wallet read routes defined by this capability under `/api/v1/wallet`
- **AND** each route has wallet-related tags
- **AND** successful responses are modeled as `ApiResponse[T]`

#### Scenario: OpenAPI 不展示 wallet 写操作
- **WHEN** tests inspect `/openapi.json`
- **THEN** the schema contains no wallet account creation, cash adjustment, paper order write, paper execution write or wallet facts frontend route for this capability

### Requirement: Wallet API 文案保持 only 虚盘，不操作实盘

Portfolio Wallet API V1 SHALL describe the capability as paper-only and avoid live trading implications.

#### Scenario: Endpoint 和 schema 命名不暗示实盘能力
- **WHEN** route paths, schema names, tags, descriptions or tests describe wallet API V1
- **THEN** they identify paper account, paper order or paper execution concepts where relevant
- **AND** they do not imply live broker sync, live order placement, real cancellation, real modification, real FX transfer or real cash transfer support

#### Scenario: WalletFacts 不作为前端查询资源
- **WHEN** API routes are implemented for this capability
- **THEN** they do not expose `WalletFacts` as a frontend endpoint
- **AND** Policy Gate or risk check consumption remains a separate capability
