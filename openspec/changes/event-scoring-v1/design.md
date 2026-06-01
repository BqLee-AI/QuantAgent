## Context

评分体系已经在 PRD 中完成产品语义收口，但还没有形成实现前可依赖的 OpenSpec 行为契约。当前相关真源分工如下：

- `docs/prd/09-scoring-and-prioritization.md`：定义用户可见评分层、页面使用规则、异常和降级展示。
- `docs/prd/pages/00-dashboard.md`、`02-events-home.md`、`03-event-detail.md`、`04-approvals-index.md`、`05-approval-detail.md`：定义各页面任务和风险边界。
- `openspec/changes/web-p0-mainflow-pages/`：定义 Web P0 主链路页面职责，但不定义评分字段、排序语义、降级规则和 mock 收口。
- `apps/web/src/features/mainflow/mock-data.ts`：当前首页骨架存在 `priority`、`referenceStrength`、`industryImpact` 等临时字段，只能视为 mock 表达，不能成为正式 contract。

本 change 的上游目标仍然是把“评分体系如何进入页面和契约”收成后续 Web/API/contracts 实现必须回链的真源；当前 PR 额外包含基于 mock data 的 Web 展示脚手架，用来验证这些评分语义在页面上的落点，但不包含真实 API/contracts 接入。

## Goals / Non-Goals

**Goals:**

- 固化评分体系与首页基础 UI 的阶段切分，避免 Dashboard 首版被正式评分字段阻塞。
- 固化 `/events` 为评分首次正式接入面。
- 固化 Dashboard、Event Detail、Approvals / Approval Detail 的评分消费边界。
- 固化用户可见评分层的最小字段语义、展示用途和禁止混用规则。
- 固化评分缺失、冲突、分析失败、事件过期、Policy Gate 阻断时的降级展示要求。
- 固化后续 API DTO、`packages/contracts`、mock data 和前端类型命名的收口方向。

**Non-Goals:**

- 不实现评分算法、权重、prompt、训练、回测、个性化排序或交易胜率估计。
- 不修改 `apps/web` 页面、API route、`packages/contracts`、数据库迁移或 generated client。
- 不定义真实执行放行、broker 行为、Policy Gate 后端策略或批量审批策略。
- 不要求 Dashboard 首版变成评分驱动首页。

## Decisions

### 1. 使用独立 `event-scoring-v1` capability，而不是扩写 `web-p0-mainflow-pages`

`web-p0-mainflow-pages` 负责回答“页面各自负责什么”。评分体系需要回答的是“哪些评分层存在、先进入哪个页面、各页面消费哪些摘要、失败时如何降级、字段命名如何收口”。

把这些规则继续塞进页面 capability 会让页面职责与评分行为耦合，后续 API/contracts 或审批实现也难以回链。因此本 change 独立成 capability，只通过页面消费矩阵引用 P0 主链路页面。

### 2. Dashboard 首版不依赖正式评分字段

Dashboard / 首页第一版先交付普通事件展示、待审批摘要、健康提醒和主工作入口。正式评分字段、排序、高价值判定不作为首页基础 UI 的前置条件。

当前首页 mock 中类似评分的字段只服务骨架展示。后续评分接入时必须替换为正式评分语义，不能把这些临时字段扩散到 API DTO、contracts 或长期 mock data。

替代方案是立即要求 Dashboard 改造成评分驱动首页。该方案会反向阻塞基础 UI，并与已确认的阶段切分冲突，因此不采用。

### 3. `/events` 是评分首次正式接入面

评分体系第一次落地需要同时支撑：

- 重点事件区和普通事件列表的区分。
- “最新 + 高价值混合”“最新优先”“高价值优先”等排序。
- 时间、行业、可信度、分析状态、来源类型等筛选。
- 高价值事件入选原因。
- 对低可信、冲突、分析失败、过期事件的显式标签。

这些能力属于事件集合工作台，天然落在 `/events`，而不是 Dashboard 或 Event Detail。Dashboard 后续只消费少量重点摘要；Event Detail 负责解释单条事件的评分含义和不确定性。

### 4. 用户可见评分必须分层，不能用单一 `priority` 或 `score`

正式契约至少需要区分以下语义：

| 字段语义 | 回答的问题 | 主要消费面 |
| --- | --- | --- |
| `source_authority` | 来源是否权威 | Dashboard、Events、Event Detail、Approval Detail |
| `event_reliability` | 事件是否可信 | Dashboard、Events、Event Detail、Approval Detail |
| `impact_strength` | 属实后影响多大 | Dashboard、Events、Event Detail |
| `freshness` | 是否还在处理窗口 | Dashboard、Events、Approvals |
| `event_priority` | 当前时间窗先看哪条 | Dashboard、Events |
| `analysis_confidence` | 系统分析是否稳定 | Event Detail、Approval Detail |
| `recommendation_score` | 建议是否值得人工确认 | Event Detail、Approvals |
| `verification_status` | 验证处于什么状态 | Events、Event Detail、Approval Detail |
| `uncertainty_summary` | 主要不确定性是什么 | Event Detail、Approval Detail |

审批相关的 `risk_direction`、`risk_level`、`confirmation_level` 与评分摘要相邻展示，但不是评分层本身。它们属于人工确认和风险治理语义，必须保持独立。

### 5. 页面只消费与任务匹配的评分摘要

本 change 不要求所有页面一次性接完整评分体系：

- `/events` 首轮消费 `event_priority`、`event_reliability`、`impact_strength`、`freshness`、`verification_status`、分析状态、涉及行业和入选原因。
- Dashboard 后续只消费少量重点事件摘要：`event_priority`、`event_reliability`、`impact_strength`、`freshness` 和入选原因。
- Event Detail 展示解释性评分：`source_authority`、`event_reliability`、`impact_strength`、`analysis_confidence`、`recommendation_score`、`verification_status`、`uncertainty_summary`。
- Approvals / Approval Detail 展示确认相关上下文：`recommendation_score`、事件可信度摘要、分析置信度摘要、`risk_direction`、`risk_level`、`confirmation_level`、到期策略和阻断原因。

### 6. 降级规则必须进入可验收契约

评分会影响操盘者优先级判断，因此失败路径不能留给页面实现猜测：

- 单一低权威来源：展示弱来源、低可信或待验证，不表达成高置信重点事件。
- 多信源冲突：降低事件可信度并展示冲突摘要。
- 工具失败或关键数据缺口：影响分析置信度，不展示看似完整的建议推荐度。
- 事件过期、被覆盖或被澄清：降低时效性，移出高价值首屏重点位。
- 分析输出无效：展示分析失败，允许重分析或人工复核。
- Policy Gate 阻断：展示阻断原因和 request / trace 标识，不把高分表达成可执行结论。

### 7. 后续实现必须按职责拆分，不在 mainflow 骨架里继续堆评分逻辑

本 change 不直接改代码，但后续实现进入 `apps/web` 时必须遵守 Web gate：

- route 只负责 `createFileRoute`、search params、loader / beforeLoad 和页面组合。
- 正式事件中心应落在独立事件 feature 边界或等价职责目录内，至少拆出 `api/`、`queries/`、`hooks/`、`components/`、`types/`、`utils/` 和 `README.md`。
- API 调用链路遵守 `app/runtime -> apiClient -> BaseApi -> FeatureApi -> queries/mutations -> business hooks -> view components`。
- 评分 label、等级映射、排序参数、筛选参数和空/错/降级状态不能散落在 route 或展示组件内。
- `features/mainflow` 可以继续承接当前静态骨架，但正式评分接入不应继续把 API、DTO、query、筛选状态和评分解释塞入现有 `EventPages.tsx` 或 mock 文件。

后续 contract/API 实现需要单独 change 或在实现 PR 中明确写入：

- API DTO / schema 字段草案与来源。
- `packages/contracts` 是否作为跨语言契约真源。
- generated client 或手写 contract 的生成/验证命令。
- mock data 与正式字段的同步策略。

## Data Flow Blueprint

后续正式实现的数据流应收敛为：

```text
Source Plugin / Industry Analysis / Decision input
  -> Event / ScoredAnalysis / DecisionResult REST snapshot
  -> API DTO or packages/contracts scoring summary
  -> Web FeatureApi
  -> TanStack Query list/detail hooks
  -> page business hooks for filters, sorting, and degradation labels
  -> Events / Dashboard / Event Detail / Approvals view components
```

WebSocket 或实时通道只能触发 query invalidation，不作为评分状态真源。评分摘要的恢复与刷新必须以 REST、数据库和审计记录为准。

## Validation Strategy

本 OpenSpec-only change 的最小验证：

- `openspec validate event-scoring-v1 --type change --strict --json`
- 人工核对本 change 与 `docs/prd/09-scoring-and-prioritization.md` 以及五个页面 PRD 的页面语义一致。
- 人工核对没有把 `event_priority`、`analysis_confidence` 或 `recommendation_score` 写成执行放行、胜率或自动下单信号。

后续 Web/API/contracts 实现的验证入口应至少包括：

- `git diff --check`
- Web 构建或受影响测试，例如 `bun run --cwd apps/web build`
- API/contracts 的 schema 或类型检查命令，以具体实现 PR 为准
- 页面人工验收：低可信、冲突、分析失败、过期、Policy Gate 阻断和评分缺失状态均可见

## Risks / Trade-offs

- [Risk] 本轮只新增 OpenSpec 文档，不清理首页 mock 临时字段。
  Mitigation：spec 和 tasks 明确临时字段不得成为正式 contract，后续实现必须收口。

- [Risk] `event-scoring-v1` 与 PRD 页面规则存在重复。
  Mitigation：PRD 负责产品语义，OpenSpec 负责可验证行为、阶段接入和实现前置边界。

- [Risk] `/events` 先接评分可能被误解为 Dashboard 不再展示重点事件。
  Mitigation：spec 明确 Dashboard 后续仍消费重点摘要，只是不作为首次正式接入面。

- [Risk] 后续 API/contracts 先行实现时再次分叉字段命名。
  Mitigation：tasks 要求 API DTO、`packages/contracts`、mock data 和前端类型同源回链本 change。
