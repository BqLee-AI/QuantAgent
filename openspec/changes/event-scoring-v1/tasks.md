## 1. OpenSpec-only 收口

- [x] 1.1 完成 `proposal.md`，说明 why now、当前缺口、非目标、影响面和 OpenSpec-only 边界。
- [x] 1.2 完成 `design.md`，固定 `/events` 为评分首次正式接入面，并补齐页面消费矩阵、字段语义、数据流、失败路径、后续职责拆分和验证策略。
- [x] 1.3 完成 `specs/event-scoring-v1/spec.md`，覆盖阶段切分、评分分层、页面消费、降级展示、执行权限边界和 contract / mock 收口要求。
- [x] 1.4 对齐 `docs/prd/09-scoring-and-prioritization.md` 的阶段约束：首页首版不做评分前置、`/events` 优先接入、临时 mock 字段后续收口。

## 2. 后续实现前置 Gate

- [ ] 2.1 后续 `/events` 评分实现必须先明确 API DTO / `packages/contracts` 字段来源，再接入真实服务端数据源，替换当前前端局部 mock contract。
- [x] 2.2 后续 Web 实现必须按 feature 职责拆分 route、api、contracts、query keys、queries、hooks、components、types、utils 和 README，不把正式评分 API、筛选、排序或解释逻辑继续堆进 `features/mainflow` 的静态骨架文件。
- [x] 2.3 后续 Dashboard 只消费少量重点事件评分摘要，不作为评分首次正式落地点，也不承担完整评分解释和事件筛选职责。
- [x] 2.4 后续 Event Detail 必须补来源权威度、事件可信度、行业影响强度、分析置信度、建议推荐度、验证状态和不确定性摘要，并保持事件事实、评分解释、建议动作分层。
- [x] 2.5 后续 Approvals / Approval Detail 必须同时展示建议推荐度、事件可信度摘要、分析置信度摘要、风险方向、风险等级、确认等级和到期策略。
- [x] 2.6 后续 API DTO、`packages/contracts`、generated client、mock data 和前端字段命名必须从首页骨架期的临时字段收口到正式评分语义。
- [x] 2.7 后续实现必须覆盖低权威单信源、多信源冲突、工具失败、分析输出无效、事件过期和 Policy Gate 阻断的降级展示。

## 3. 验证与 Review

- [x] 3.1 运行 `openspec validate event-scoring-v1 --type change --strict --json`，确认 change 校验通过。
- [x] 3.2 人工核对本 change 与 `docs/prd/09-scoring-and-prioritization.md`、`docs/prd/pages/00-dashboard.md`、`02-events-home.md`、`03-event-detail.md`、`04-approvals-index.md`、`05-approval-detail.md` 的页面语义一致。
- [x] 3.3 人工核对本 change 没有把建议推荐度、事件优先级或分析置信度写成执行放行分、胜率、收益预期或自动下单信号。
- [x] 3.4 后续若提交 PR，先按仓库规则创建 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入代码实现。
