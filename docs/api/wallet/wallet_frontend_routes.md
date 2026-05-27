# QuantAgent Wallet API 前端对接说明

本文整理当前前端需要直接对接的 Wallet 接口，用于账户总览、现金余额、持仓、流水、模拟订单和成交展示。

## 基本信息

- Base Path: `/api/v1/wallet`
- 路由标签：`wallet`
- 响应格式统一为 `code/data/msg/error`
- 全部接口都属于受保护接口，需要有效登录态 Cookie
- 当前接口族全部为只读查询，不需要 `X-CSRF-Token`
- 当前实现只支持 `paper` 账户

## 为什么需要前端对接

- 这些路由已经通过 `register_api_v1_routes` 作为 `protected` API 注册到 `/api/v1`
- 返回 DTO 已经做过 API 传输层映射，不依赖内部 ORM 或 Python 对象
- 字段设计明显面向管理台展示，而不是仅供后端内部调用

因此，`wallet` 应视为前端资产页/账户页直接消费的 HTTP API。

## 统一响应格式

成功响应示例：

```json
{
  "code": 0,
  "data": {},
  "msg": "ok",
  "error": null
}
```

错误响应示例：

```json
{
  "code": 40400,
  "data": null,
  "msg": "Wallet account not found",
  "error": {
    "code": "NOT_FOUND",
    "request_id": "req-123",
    "trace_id": null,
    "details": {
      "account_id": "paper-main"
    },
    "retryable": false
  }
}
```

## 路由总览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/accounts/{account_id}` | 查询单个交易账户概览 |
| GET | `/accounts/{account_id}/cash-balances` | 查询账户现金余额列表 |
| GET | `/accounts/{account_id}/positions` | 查询账户持仓列表 |
| GET | `/accounts/{account_id}/ledger-entries` | 查询账户资金流水，可带 `limit` |
| GET | `/accounts/{account_id}/paper-orders` | 查询模拟订单列表 |
| GET | `/accounts/{account_id}/paper-executions` | 查询模拟成交列表 |

## 鉴权规则

- 所有接口都需要有效 session Cookie
- 前端请求需要带 `credentials: "include"` 或 axios `withCredentials: true`
- 当前接口都是 GET，不需要 `X-CSRF-Token`
- session 失效时返回 `401`
- 账户不存在时返回 `404`

## 详细说明

### 1. `GET /api/v1/wallet/accounts/{account_id}`

用途：拉取账户基础信息，用于账户标题区、账户模式、基础币种等展示。

成功返回 `data` 示例：

```json
{
  "account_id": "paper-main",
  "name": "Primary Paper Account",
  "mode": "paper",
  "base_currency": "USD",
  "created_at": "2026-05-20T08:00:00Z"
}
```

字段说明：

- `mode` 当前固定为 `paper`
- `base_currency` 可作为金额展示默认币种

### 2. `GET /api/v1/wallet/accounts/{account_id}/cash-balances`

用途：展示账户现金余额卡片或多币种余额表。

成功返回 `data` 示例：

```json
[
  {
    "account_id": "paper-main",
    "currency": "USD",
    "total": "100000.00000000",
    "available": "98000.00000000",
    "locked": "2000.00000000",
    "unsettled": "0.00000000",
    "updated_at": "2026-05-20T09:30:00Z"
  }
]
```

前端注意：

- 当前金额字段按 wallet core 的 8 位定点语义序列化为字符串；前端不要直接按 JS `number` 做精度敏感运算
- `available`、`locked`、`unsettled` 可以拆成余额明细

### 3. `GET /api/v1/wallet/accounts/{account_id}/positions`

用途：展示当前持仓表。

成功返回 `data` 示例：

```json
[
  {
    "account_id": "paper-main",
    "instrument": "AAPL",
    "market": "NASDAQ",
    "side": "long",
    "quantity": "10.00000000",
    "sellable_quantity": "10.00000000",
    "average_cost": "180.50000000",
    "market_value": "1850.00000000",
    "unrealized_pnl": "45.00000000",
    "currency": "USD",
    "updated_at": "2026-05-20T09:31:00Z"
  }
]
```

前端注意：

- `side` 当前只有 `long`
- `instrument + market` 可作为列表主键的一部分
- 数量和金额字段当前都按 8 位定点字符串返回，展示层可按需要裁剪尾随 `0`

### 4. `GET /api/v1/wallet/accounts/{account_id}/ledger-entries`

用途：展示账户资金流水或审计流水。

查询参数：

- `limit`: 可选，必须大于 0

成功返回 `data` 示例：

```json
[
  {
    "entry_id": "ledger-001",
    "account_id": "paper-main",
    "entry_type": "trade",
    "currency": "USD",
    "amount": "-1805.00000000",
    "source_type": "paper_execution",
    "source_ref": "exec-001",
    "occurred_at": "2026-05-20T09:32:00Z",
    "order_id": "order-001",
    "execution_id": "exec-001",
    "metadata": {
      "instrument": "AAPL"
    },
    "created_at": "2026-05-20T09:32:01Z"
  }
]
```

错误约定：

- `limit <= 0` 会被请求参数校验拦截，返回 `422`

### 5. `GET /api/v1/wallet/accounts/{account_id}/paper-orders`

用途：展示模拟交易订单列表。

成功返回 `data` 示例：

```json
[
  {
    "order_id": "order-001",
    "account_id": "paper-main",
    "client_order_id": "client-001",
    "instrument": "AAPL",
    "market": "NASDAQ",
    "side": "buy",
    "order_type": "limit",
    "quantity": "10.00000000",
    "limit_price": "180.50000000",
    "currency": "USD",
    "status": "filled",
    "requested_at": "2026-05-20T09:31:00Z",
    "completed_at": "2026-05-20T09:32:00Z"
  }
]
```

前端注意：

- `order_type` 目前支持 `market`、`limit`
- `status` 目前支持 `open`、`filled`、`cancelled`、`rejected`

### 6. `GET /api/v1/wallet/accounts/{account_id}/paper-executions`

用途：展示模拟成交明细。

成功返回 `data` 示例：

```json
[
  {
    "execution_id": "exec-001",
    "account_id": "paper-main",
    "order_id": "order-001",
    "idempotency_key": "idem-001",
    "instrument": "AAPL",
    "market": "NASDAQ",
    "side": "buy",
    "quantity": "10.00000000",
    "price": "180.50000000",
    "gross_amount": "1805.00000000",
    "currency": "USD",
    "fee_amount": "1.00000000",
    "fee_currency": "USD",
    "executed_at": "2026-05-20T09:32:00Z",
    "created_at": "2026-05-20T09:32:01Z"
  }
]
```

前端注意：

- `quantity`、`price`、`gross_amount`、`fee_amount` 都应按 8 位定点字符串处理

## 常见错误

| HTTP 状态码 | `code` | 场景 |
| --- | --- | --- |
| 400 | `40000` | 请求在业务上不符合要求，例如请求了非 paper 账户 |
| 401 | `40100` | 未登录或登录态失效 |
| 404 | `40400` | `account_id` 不存在 |
| 422 | `42200` | 请求参数校验失败，例如 `limit` 小于等于 0 |
| 503 | `50300` | 数据库未就绪或查询暂时不可用 |

前端建议：

- `401` 跳回登录流
- `404` 展示账户不存在或当前环境未初始化账户
- `503` 视为可重试错误，显示稍后重试

## 前端接入建议

1. 先调用账户概览接口，再并行拉取余额、持仓、流水和订单成交明细。
2. 所有金额字段按字符串十进制处理，展示时再格式化。
3. 资产页刷新可以直接重复调用这些 GET 接口，不需要带 CSRF。
4. 当前接口族没有写操作；若后续增加入金、调仓、撤单等动作，应单独补文档并明确 CSRF 和权限要求。

## 示例请求

```bash
curl -i \
  http://127.0.0.1:8000/api/v1/wallet/accounts/paper-main \
  --cookie "quantagent_session=..."
```

```bash
curl -i \
  "http://127.0.0.1:8000/api/v1/wallet/accounts/paper-main/ledger-entries?limit=20" \
  --cookie "quantagent_session=..."
```
