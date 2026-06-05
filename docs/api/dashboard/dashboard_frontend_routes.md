# QuantAgent Dashboard API 前端对接说明

本文整理 PR #295 新增的 Dashboard 聚合只读接口，用于后续管理台首页从后端 REST 快照读取重点事件、审批摘要、健康摘要和入口指标。

## 基本信息

- Base Path: `/api/v1/dashboard`
- 路由标签：`dashboard`
- 响应格式统一为 `code/data/msg/error`
- 全部接口都需要有效登录态 Cookie
- 全部接口需要 `runtime.inspect`
- 当前接口族全部为只读查询，不需要 `X-CSRF-Token`
- Dashboard summary 是 REST 快照；实时通道后续只应触发 refresh，不作为业务状态真源

## 路由总览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/summary` | 查询 Dashboard 首屏聚合摘要 |

## `GET /api/v1/dashboard/summary`

用途：拉取 Dashboard 首屏所需的后端聚合数据。

成功返回 `data` 包含四个独立分区：

| 分区 | 说明 |
| --- | --- |
| `featured_events` | 最近 24 小时重点事件预览，最多 5 条，item 结构复用 Events list item |
| `approval_summary` | pending approval 计数、24 小时内到期计数和最多 5 条预览 |
| `health_summary` | 运行健康摘要；PR #295 V1 暂未接通稳定 runtime summary，返回受控 `unavailable` |
| `entry_metrics` | 最近 24 小时事件入口指标，字段与 Events `summary_buckets` 对齐 |

每个分区结构一致：

```json
{
  "meta": {
    "status": "ok",
    "reason": null,
    "updated_at": "2026-06-05T10:01:00Z"
  },
  "data": {}
}
```

`meta.status` 可为：

| 状态 | 含义 |
| --- | --- |
| `ok` | 分区已返回可用数据 |
| `empty` | 分区查询成功但没有数据 |
| `unavailable` | 分区依赖尚未接通或暂不可用 |
| `error` | 分区查询失败，但 summary envelope 仍可返回 |

成功返回 `data` 示例：

```json
{
  "featured_events": {
    "meta": {
      "status": "ok",
      "reason": null,
      "updated_at": "2026-06-05T10:01:00Z"
    },
    "data": {
      "items": [],
      "generated_at": "2026-06-05T10:01:00Z"
    }
  },
  "approval_summary": {
    "meta": {
      "status": "ok",
      "reason": null,
      "updated_at": "2026-06-05T10:01:00Z"
    },
    "data": {
      "pending_count": 25,
      "expiring_soon_count": 0,
      "items": [
        {
          "approval_id": "approval-1",
          "summary": "adjust strategy after event",
          "risk_level": "medium",
          "expires_at": null
        }
      ]
    }
  },
  "health_summary": {
    "meta": {
      "status": "unavailable",
      "reason": "runtime_health:runtime_summary_v1_not_connected",
      "updated_at": "2026-06-05T10:01:00Z"
    },
    "data": {
      "status": "unavailable",
      "items": []
    }
  },
  "entry_metrics": {
    "meta": {
      "status": "ok",
      "reason": null,
      "updated_at": "2026-06-05T10:01:00Z"
    },
    "data": {
      "new_count": 1,
      "featured_count": 1,
      "analyzing_count": 0,
      "failed_or_review_count": 0,
      "pending_approval_count": 1
    }
  }
}
```

前端注意：

- 页面不能因为某个分区 `unavailable` 或 `error` 就丢弃整个 summary；应按分区展示降级、空态或错误态。
- `featured_events.data.items` 使用 Events list item 结构，可跳转到 `/events/{event_id}` 并通过 Events detail API 恢复详情。
- Dashboard V1 当前不提供查询参数，`featured_events` 与 `entry_metrics` 统一使用最近 24 小时窗口；需要其他窗口时应调用 Events list API。
- `approval_summary.data.pending_count` 和 `expiring_soon_count` 是独立计数，不受预览列表最多 5 条限制。
- `health_summary` 在 V1 明确返回 `unavailable`，前端不能用 mock 或 runtime fixture 静默填成真实健康数据。
- Dashboard 不承接交易执行语义；事件推荐、审批摘要和健康摘要只用于导航和判断入口。

## 常见错误

| HTTP 状态码 | `code` | 场景 |
| --- | --- | --- |
| 401 | `40100` | 未登录或登录态失效 |
| 403 | `40300` | 缺少 `runtime.inspect` |
| 503 | `50300` | 数据库 session 不可用 |
