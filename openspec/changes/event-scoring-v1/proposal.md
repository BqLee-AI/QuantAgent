## Why

QuantAgent 已经有两层真源：

- `docs/prd/09-scoring-and-prioritization.md` 定义了来源权威度、事件可信度、行业影响强度、时效性、事件综合优先级、分析置信度、建议推荐度、风险方向和确认等级的产品语义。
- `web-p0-mainflow-pages` 与页面 PRD 定义了 Dashboard、`/events`、`/events/:eventId`、`/approvals` 和审批详情的页面职责。

缺口在于：评分体系何时进入 Web 主链路、第一次落在哪个页面、页面之间如何分工、以及首页 mock 中已有的 `priority`、`referenceStrength`、`industryImpact` 等临时字段如何收口，还没有被固化成可 review、可验证的 OpenSpec 契约。

如果不单独收口，后续 `/events`、Dashboard、事件详情、审批页、API DTO、`packages/contracts` 和 mock data 容易各自发明评分字段，甚至把事件优先级、分析置信度或建议推荐度误表达成执行许可。

## What Changes

- 新增 `event-scoring-v1` capability，作为评分展示与高价值事件判定进入 Web P0 主链路的 OpenSpec 上游。
- 固化阶段边界：Dashboard / 首页第一版先跑通普通事件展示与 mock 骨架，不把正式评分字段作为前置依赖。
- 固化首次正式接入面：评分体系第一次进入页面能力时，优先落在 `/events` 事件中心，用于承接高价值事件判定、排序、筛选和评分摘要。
- 固化页面消费矩阵：Dashboard 只消费少量重点摘要；Event Detail 承接解释与不确定性；Approvals / Approval Detail 承接人工确认上下文。
- 固化评分边界：高价值事件、建议推荐度和分析置信度都不是执行放行分，不能绕过 Decision / Policy Gate。
- 固化 contract / mock 收口方向：后续 API DTO、`packages/contracts`、mock data 和前端字段命名必须回链正式评分语义，不沿用首页骨架期临时字段。

## Out Of Scope

- 不实现评分算法、权重、模型提示词、训练、回测或个性化排序。
- 不直接修改真实 API DTO、`packages/contracts`、generated client、`apps/api` 或数据库模型；当前允许包含基于 mock data 的 `apps/web` 展示脚手架来验证评分语义落点。
- 不定义 broker 执行放行、真实交易、批量审批策略或 Policy Gate 后端行为。
- 不把 Dashboard 首版重新拉回评分驱动首页，也不要求所有页面一次性接完整评分明细。

## Capabilities

### New Capabilities

- `event-scoring-v1`: 定义多层评分体系在 Web P0 主链路中的阶段接入、页面消费边界、降级展示、执行权限边界和后续 contract / mock 收口要求。

### Modified Capabilities

- 无。`web-p0-mainflow-pages` 继续定义页面职责；本 change 只补评分接入与展示语义。

## Impact

- OpenSpec：新增 `openspec/changes/event-scoring-v1/specs/event-scoring-v1/spec.md`，作为评分展示与高价值事件接入的上游契约。
- 产品真源：与 `docs/prd/09-scoring-and-prioritization.md`、Dashboard、Events、Event Detail、Approvals 和 Approval Detail 页面 PRD 对齐。
- Web 后续实现：`/events` 后续实现必须优先消费正式评分摘要字段；Dashboard 只补重点摘要，不成为首次评分落地点。
- Contract 后续实现：API DTO、`packages/contracts`、mock data 和前端类型需要按正式评分语义收口，并在实现 PR 中回链本 change。
- Review 流程：本 change 属于 OpenSpec-only PR 输入；进入代码实现前需要维护者明确评论“没问题”或批准。
