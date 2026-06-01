## ADDED Requirements

### Requirement: Dashboard V1 Baseline Does Not Depend On Formal Scoring

系统 SHALL 将 Dashboard / 首页基础 UI 与正式评分体系接入拆成两个阶段，避免首页第一版因为缺少正式评分字段、排序或高价值事件判定而被阻塞。

#### Scenario: Dashboard baseline can ship with ordinary event mock data
- **WHEN** 团队实现或调整 Dashboard / 首页第一版基础 UI
- **THEN** 页面可以先使用普通事件展示和 mock 骨架
- **AND** 不要求正式评分字段、评分排序或高价值事件判定已经接入
- **AND** 不将评分体系作为首页基础 UI 的前置门槛

#### Scenario: Homepage score-like mock fields are temporary
- **WHEN** 首页骨架或 mock data 中存在 `priority`、`referenceStrength`、`industryImpact` 或同类临时字段
- **THEN** 这些字段只用于基础 mock 展示
- **AND** 不被视为 API、`packages/contracts`、generated client、前端类型或页面语义的正式命名
- **AND** 后续评分接入时必须收口到正式评分语义

### Requirement: Events Is The First Formal Scoring Surface

系统 SHALL 将 `/events` 定义为评分体系第一次正式进入 Web 页面能力的落地点，用于承接高价值事件判定、排序、筛选和评分摘要展示。

#### Scenario: Events consumes the first formal scoring summary
- **WHEN** 团队开始将评分体系正式接入 Web 页面
- **THEN** `/events` 首先消费事件评分摘要
- **AND** 评分摘要至少区分事件综合优先级、事件可信度、行业影响强度和时效性
- **AND** Dashboard、Event Detail 和 Approvals 的评分接入不得早于 `/events` 的首轮字段语义收口

#### Scenario: Events explains high-value selection
- **WHEN** `/events` 展示重点事件区或事件列表
- **THEN** 用户可以看到某条事件为什么被判定为高价值
- **AND** 页面展示入选原因、验证状态或同等解释信息
- **AND** 不把高价值事件判定退化成只有一个无法解释的总分

#### Scenario: Events sorting and filters preserve scoring semantics
- **WHEN** `/events` 提供排序或筛选能力
- **THEN** 最新优先、高价值优先、最新 + 高价值混合、可信度、行业、分析状态和来源类型等语义必须与正式评分摘要分层一致
- **AND** 不用单一 `priority` 字段同时承担时间、可信度、影响强度和分析状态

### Requirement: User-Facing Scores Remain Layered

系统 SHALL 将用户可见评分拆成不同判断层，而不是使用单一 `priority` 或单一 `score` 混合表达可信度、重要性、分析稳定性和建议推荐度。

#### Scenario: Formal scoring fields keep distinct meanings
- **WHEN** 前端、API DTO、`packages/contracts` 或 mock data 定义正式评分摘要
- **THEN** 至少区分 `source_authority`、`event_reliability`、`impact_strength`、`freshness`、`event_priority`、`analysis_confidence`、`recommendation_score`、`verification_status` 和 `uncertainty_summary`
- **AND** 不将“事件是否为真”“事件影响多大”“现在是否值得先看”“系统分析是否稳定”“建议是否值得人工确认”混成同一个字段

#### Scenario: Approval risk semantics stay separate from scoring
- **WHEN** 审批列表或审批详情展示评分相关信息
- **THEN** `risk_direction`、`risk_level` 和 `confirmation_level` 与评分摘要分开表达
- **AND** 不把风险方向、风险等级或确认等级误写成评分层的一部分

### Requirement: Pages Consume Only Task-Appropriate Scoring Summaries

系统 SHALL 按页面任务分配评分摘要，避免所有页面一次性承接完整评分明细或互相复制职责。

#### Scenario: Dashboard consumes only highlighted-event summary
- **WHEN** Dashboard 在后续阶段展示评分相关摘要
- **THEN** 页面只消费少量重点事件评分摘要
- **AND** 摘要至少围绕事件综合优先级、事件可信度、行业影响强度、时效性和入选原因组织
- **AND** Dashboard 不承担完整评分解释页、事件筛选页或审批工作台职责

#### Scenario: Event Detail explains scoring and uncertainty
- **WHEN** `/events/:eventId` 后续展示评分信息
- **THEN** 页面优先展示来源权威度、事件可信度、行业影响强度、分析置信度、建议推荐度、验证状态和不确定性摘要
- **AND** 用户能够分清事件事实、评分解释和建议动作
- **AND** 页面不展示完整模型推理链

#### Scenario: Approvals focus on confirmation context
- **WHEN** `/approvals` 或审批详情展示评分相关信息
- **THEN** 页面展示建议推荐度、事件可信度摘要、分析置信度摘要、风险方向、风险等级、确认等级和到期策略
- **AND** 页面不将审批列表退化成只有一个推荐分和操作按钮

### Requirement: Scoring Must Not Be Presented As Execution Permission

系统 SHALL 将评分与执行权限严格区分，避免前端把高价值事件、建议推荐度或分析置信度表达成可直接执行的信号。

#### Scenario: High score does not imply execution approval
- **WHEN** 页面展示 `event_priority`、`analysis_confidence` 或 `recommendation_score`
- **THEN** UI 语义只表示事件判断、分析稳定性或人工确认优先级
- **AND** 不将这些字段写成执行通过率、胜率、收益预期或已可下单信号

#### Scenario: Decision and Policy Gate remain visible
- **WHEN** 某条事件或建议同时具有高评分和审批 / 策略限制
- **THEN** 页面仍需展示审批入口、阻断原因、确认等级或 request / trace 标识
- **AND** 不允许前端因为评分高而绕过 Decision / Policy Gate

### Requirement: Scoring Degrades Explicitly On Conflicts, Failures, And Staleness

系统 SHALL 在评分输入不完整、互相冲突、分析失败或事件过期时给出显式降级语义，而不是继续维持高价值事件展示。

#### Scenario: Weak or unverified source does not produce high-confidence display
- **WHEN** 事件只来自低权威单一来源或仍处于待验证状态
- **THEN** 页面显示低可信、弱来源或待验证语义
- **AND** 该事件不被表达成高置信重点事件

#### Scenario: Conflicting sources reduce confidence
- **WHEN** 同一事件存在多信源冲突
- **THEN** 页面降低事件可信度
- **AND** 展示冲突摘要而不是只显示一个表面分值

#### Scenario: Analysis failure removes recommendation-style certainty
- **WHEN** 工具调用失败、分析输出无效或关键数据缺口阻断评分
- **THEN** 页面显式展示分析置信度受影响、分析失败或数据缺口
- **AND** 不展示看似完整的建议推荐度结论

#### Scenario: Stale events lose high-value prominence
- **WHEN** 事件已过期、已被后续事件覆盖或已被澄清
- **THEN** 页面降低时效性
- **AND** 事件不继续占用高价值事件首屏重点位

#### Scenario: Policy blocking is displayed as a gate, not a score
- **WHEN** Policy Gate、审批策略或权限限制阻断某条建议
- **THEN** 页面展示阻断原因、确认等级或 request / trace 标识
- **AND** 不通过提高或降低评分来替代阻断解释

### Requirement: Future Contracts And Mock Data Converge On Formal Scoring Names

系统 SHALL 要求后续 API DTO、`packages/contracts`、mock data 和前端字段命名回链正式评分语义，而不是长期保留骨架期的临时命名。

#### Scenario: Formal contracts replace temporary homepage labels
- **WHEN** 后续实现开始为 Web、API 或 `packages/contracts` 增加正式评分字段
- **THEN** 命名必须回链 `source_authority`、`event_reliability`、`impact_strength`、`freshness`、`event_priority`、`analysis_confidence`、`recommendation_score`、`verification_status` 和 `uncertainty_summary` 这类正式语义
- **AND** 不继续把 `priority`、`referenceStrength`、`industryImpact` 或同类临时字段扩散成正式 contract

#### Scenario: Mock data follows contract semantics
- **WHEN** 前端 mock data 需要支持评分展示、排序或筛选
- **THEN** mock 字段语义与正式评分 contract 保持一致
- **AND** 页面组件不额外维护另一套平行评分解释

#### Scenario: Web implementation uses feature boundaries for formal scoring
- **WHEN** 后续 Web 实现正式接入评分 API、query、筛选、排序或评分解释
- **THEN** route 只负责入口、search params 和页面组合
- **AND** API、contract 类型、query hooks、业务 hooks、组件、格式化工具和 README 必须按 feature 职责拆分
- **AND** 不把正式评分数据流继续堆进首页骨架 mock 或单个厚页面文件
