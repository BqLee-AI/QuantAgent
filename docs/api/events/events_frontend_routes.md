# QuantAgent Events API 前端对接说明

本文整理 PR #295 新增的标准 Event read model 只读接口，用于后续 Dashboard、事件中心和事件详情页从后端 REST 快照恢复状态。

## 基本信息

- Base Path: `/api/v1/events`
- 路由标签：`events`
- 响应格式统一为 `code/data/msg/error`
- 全部接口都需要有效登录态 Cookie
- 全部接口需要 `runtime.inspect`
- 当前接口族全部为只读查询，不需要 `X-CSRF-Token`
- 标准 Event API 是管理台业务事件快照入口；RawEvent、runtime audit news、Agent run 和 Tool invocation 是相关审计或运行态视角，不能替代本接口

## 路由总览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 查询标准事件列表、筛选回显、summary buckets 和分页游标 |
| GET | `/{event_id}` | 查询事件详情摘要、评分、最佳动作、运行引用、证据摘要和状态流转 |

## `GET /api/v1/events`

用途：拉取事件中心列表，也可作为 Dashboard 以外的标准事件列表数据源。

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `time_range` | `today` / `24h` / `7d` / `30d` | `24h` | 时间范围 |
| `industry` | string[] | `[]` | 行业筛选，可重复传参 |
| `credibility` | string | `null` | 可信度筛选 |
| `analysis_status` | string | `null` | 分析状态筛选 |
| `source_type` | string | `null` | 来源类型筛选 |
| `sort` | `mixed` / `latest` / `priority` | `mixed` | 排序方式 |
| `cursor` | string | `null` | 游标分页 |
| `limit` | integer | `20` | 范围 1-100 |

成功返回 `data` 结构：

```json
{
  "items": [
    {
      "event_id": "evt-1",
      "title": "HBM supply chain improves",
      "summary": "Micron and packaging capacity trend",
      "source": {
        "name": "Example RSS",
        "authority": "example.com"
      },
      "source_type": "rss",
      "source_url": "https://example.com/hbm",
      "published_at": null,
      "captured_at": "2026-06-05T10:00:00Z",
      "current_status": "pending_approval",
      "analysis_status": "pending_approval",
      "credibility": null,
      "priority_score": 0.95,
      "recommendation_score": 0.84,
      "confidence": 0.79,
      "risk_level": "medium",
      "risk_direction": "positive",
      "industries": ["semiconductor"],
      "featured_reason": "priority",
      "trace_ref": { "kind": "trace", "id": "trace-api-1" },
      "raw_event_ref": { "kind": "raw_event", "id": "raw-api-1" },
      "routed_event_ref": null,
      "degradation_notices": []
    }
  ],
  "next_cursor": null,
  "filters": {
    "time_range": "7d",
    "industry": ["semiconductor"],
    "credibility": null,
    "analysis_status": null,
    "source_type": null,
    "sort": "priority",
    "limit": 20,
    "cursor": null
  },
  "summary_buckets": {
    "new_count": 1,
    "featured_count": 1,
    "analyzing_count": 0,
    "failed_or_review_count": 0,
    "pending_approval_count": 1
  },
  "generated_at": "2026-06-05T10:01:00Z"
}
```

前端注意：

- `filters` 是服务端实际采用的筛选回显，列表 UI 应以它恢复查询状态。
- `summary_buckets` 是当前筛选范围下的摘要，不是全站指标。
- `priority_score`、`recommendation_score` 和 `confidence` 只表达事件排序/建议摘要，不是交易授权或执行成功率。
- `degradation_notices` 有值时，页面应展示数据降级提示，而不是静默当作完整数据。

## `GET /api/v1/events/{event_id}`

用途：拉取事件详情页所需的标准后端摘要。

成功返回 `data` 主要包含：

- `event_id`
- `fact_summary`: 标题、摘要、来源、发布时间、捕获时间
- `score_summary`: 可信度、优先级、推荐分、置信度、风险等级和方向
- `industry_impact`: 行业影响公开摘要
- `best_action`: 建议动作公开摘要、推荐分、置信度、风险信息和 approval 引用
- `approval_ref`: 关联 approval 资源引用
- `runtime_summary`: 最新 Agent run、Tool invocation、trace 和 correlation 引用
- `evidence_summary`: 公开证据摘要
- `degradation_notices`: 降级提示
- `audit_refs`: 相关审计引用
- `state_summary`: 当前状态、分析状态、版本和 append-only 状态流转

`best_action` 示例：

```json
{
  "title": "Review strategy",
  "action_hint": "open approval",
  "recommendation_score": 0.84,
  "confidence": 0.79,
  "risk_level": "medium",
  "risk_direction": "positive",
  "approval_ref": { "kind": "approval", "id": "approval-api-1" },
  "status": null,
  "unavailable_reason": null
}
```

前端注意：

- `best_action` 只表达建议和审批入口，不表示已通过 Policy Gate、已下单或真实 broker 成交。
- 详情响应不会返回完整 prompt、provider raw response、secret、broker credential 或私有策略原文。
- 未知 `event_id` 返回统一 `404` envelope，并在 `error.details.event_id` 带回查询 ID。
- 状态恢复应以本接口为真源；实时通道后续只能触发重新拉取。

## 常见错误

| HTTP 状态码 | `code` | 场景 |
| --- | --- | --- |
| 400 | `40000` | 查询参数非法，例如不支持的 `sort` |
| 401 | `40100` | 未登录或登录态失效 |
| 403 | `40300` | 缺少 `runtime.inspect` |
| 404 | `40400` | `event_id` 不存在 |
| 503 | `50300` | 数据库 session 不可用 |
