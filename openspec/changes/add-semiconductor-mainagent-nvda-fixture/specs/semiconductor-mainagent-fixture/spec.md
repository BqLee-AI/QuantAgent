## ADDED Requirements

### Requirement: 半导体行业包声明 MainAgent 资产
系统 SHALL 在半导体行业包中声明可由 `AgentRuntime` 加载的 MainAgent 资产，包括 prompt、skill、tool profile、输出约束和 fixture 入口；行业包不得直接创建或运行 DeepAgents 实例。

#### Scenario: 行业包资产由 runtime 加载
- **WHEN** 平台或测试 loader 读取半导体行业包资产
- **THEN** loader 能构造通用 `AgentDefinition`、`SubAgentDefinition` 和 `ToolProfile`
- **AND** 行业包代码不直接调用 `create_deep_agent()` 或绕过 `AgentRuntime`

#### Scenario: MainAgent 工具 profile 精简
- **WHEN** MainAgent definition 被加载
- **THEN** 其工具集合只包含 `get_run_context`、`search_web`、`get_account_context`、`evaluate_thesis`、`build_action_plan`、`submit_action_plan`
- **AND** 不包含直接通知、审批、broker、监控或底层交易执行工具

### Requirement: Research SubAgent 最小权限
系统 SHALL 为半导体 MVP 只固定一个可选 `evidence_research_analyst` SubAgent，并限制其只能读取 run context 和执行搜索，不得读取账户、生成交易计划或提交动作。

#### Scenario: Research SubAgent 工具 profile 不含账户工具
- **WHEN** `evidence_research_analyst` definition 被加载
- **THEN** 其工具集合只包含 `get_run_context` 和 `search_web`
- **AND** 不包含 `get_account_context`、`build_action_plan`、`submit_action_plan` 或任何 broker / notification / approval 工具

#### Scenario: SubAgent 任务说明完整
- **WHEN** MainAgent 委派 `evidence_research_analyst`
- **THEN** 任务 instruction 包含当前事件摘要、目标、允许工具、搜索预算、输出格式、停止条件和禁止事项
- **AND** MainAgent 不假设该 SubAgent 记得前一次任务上下文

### Requirement: 通用证据产物和 ID-first 传递
系统 SHALL 通过通用 `EvidenceBoard`、`EvidenceResearchReport`、`ArtifactRef`、`ThesisEvaluation`、`ActionPlan` 和 `SubmitActionPlanResult` 传递有价值产物，并优先使用 ID / artifact 引用，不得为 NVDA、财报或市场预期创建专用 schema 字段。

#### Scenario: 搜索结果不直接成为证据板
- **WHEN** Agent 调用 `search_web`
- **THEN** 工具只返回搜索调用 ID、压缩结果、可选 artifact 引用和 safe summary
- **AND** `EvidenceBoard` 由 MainAgent 或 Research SubAgent 基于多次搜索和上下文读取形成

#### Scenario: 工具之间传递小引用
- **WHEN** MainAgent 调用 `evaluate_thesis`、`build_action_plan` 或 `submit_action_plan`
- **THEN** 输入优先使用 `evidence_board_artifact_id`、`industry_analysis_artifact_id`、`thesis_evaluation_artifact_id`、`account_context_id` 或 `action_plan_artifact_id`
- **AND** 不要求 Agent 复制完整搜索结果、完整账户对象或大 JSON payload

#### Scenario: 不出现财报专用字段
- **WHEN** fixture 表达市场对照、超预期、历史基准或冲突观点
- **THEN** 这些内容作为 `EvidenceBoard.claims`、`source_items`、`relation_summary` 或 `gaps` 的通用内容出现
- **AND** tool schema 中不新增 `expected_revenue`、`earnings_surprise`、`nvda_specific_*` 等场景专用字段

### Requirement: 一手财报事件触发受控 dry-run 行动
系统 SHALL 提供 NVDA 一手财报 fixture，证明 MainAgent 能在发布后约 5 分钟的一手事件上补充通用对照证据、评分、生成 ActionPlan，并通过 `submit_action_plan` 进入 mock/dry-run 受控提交。

#### Scenario: 一手事件生成 ActionPlan 并提交
- **WHEN** fixture 输入 NVDA 第一手财报公告事件，且 fake evidence / account / policy 表示证据质量高、近期无同主题行动、broker mode 为 `dry_run`
- **THEN** MainAgent 委派 `evidence_research_analyst` 产出 EvidenceBoard artifact
- **AND** MainAgent 调用 `evaluate_thesis` 得到 `suggested_intent=propose_trade`
- **AND** MainAgent 调用 `build_action_plan` 生成包含方向、仓位、止损、止盈、失效条件、监控计划和用户通知草案的 ActionPlan
- **AND** MainAgent 调用 `submit_action_plan` 一次

#### Scenario: 自动审批来自提交结果
- **WHEN** `submit_action_plan` 对一手事件返回结果
- **THEN** `SubmitActionPlanResult` 表达 `resolved_mode=execute_then_notify` 或等价 mock/dry-run 自动提交状态
- **AND** 结果包含 policy gate、dry-run broker、通知和监控摘要
- **AND** MainAgent 不在 ActionPlan 或 IndustryAnalysis 中自行声明已经审批、真实成交或绕过风控

### Requirement: 后续媒体报道 record_only 去重
系统 SHALL 提供 NVDA 后续媒体报道 fixture，证明 MainAgent 能识别同主题一手事件已经行动和通知，在没有新增实质信息时只记录分析与评分，不生成 ActionPlan、不提交动作、不重复通知。

#### Scenario: 二手报道不重复提交
- **WHEN** fixture 输入晚于一手事件约 30 分钟的 NVDA 二手媒体报道，且 fake account context 返回同主题 recent action 和 recent notification
- **THEN** MainAgent 读取近期活动并识别 `prior_coverage=fully_covered`
- **AND** `evaluate_thesis` 或等价评分结果表达 `event_relationship=follow_up` 与 `suggested_intent=record_only`
- **AND** MainAgent 不调用 `build_action_plan`
- **AND** MainAgent 不调用 `submit_action_plan`

#### Scenario: 二手报道仍产出 IndustryAnalysis
- **WHEN** 二手媒体报道被判定为已覆盖且无新增实质信息
- **THEN** run 仍产出 `IndustryAnalysis`
- **AND** `IndustryAnalysis` 引用 evidence / evaluation artifact
- **AND** `action_plan_artifact_id` 和 `submission_id` 为空
- **AND** metadata 或等价结构记录 related event、related action、related notification、trade decision 和 notification suppression 摘要

### Requirement: Fixture 无外部依赖并暴露关键 stream 事件
系统 SHALL 为半导体 MainAgent fixture 提供无外部 API key 的 fake / scripted harness，并能通过稳定 `AgentRunEvent` 验证 todo、SubAgent、tool、artifact 和最终输出。

#### Scenario: 无 secret 环境可运行
- **WHEN** 测试环境没有 LLM provider key、Tavily key、真实 broker 和真实账户 secret
- **THEN** 半导体 MainAgent fixture 测试仍可运行
- **AND** fake search、fake account、fake evaluator、fake action planner 和 fake submitter 返回结构化结果

#### Scenario: stream 事件可断言
- **WHEN** fixture run 正常完成
- **THEN** stream 至少包含 `run.started`、todo 或 planning 摘要、tool 调用摘要、artifact 创建摘要和 `run.completed`
- **AND** 一手事件 run 包含 Research SubAgent 或等价 task 摘要
- **AND** 事件 payload 不暴露 secret、完整 prompt、完整 provider raw response 或完整工具堆栈
