## ADDED Requirements

### Requirement: Dashboard Is the Operator Home

系统 SHALL 将 Dashboard 作为已登录操盘者进入管理台后的默认判断面板，而不是把事件中心作为系统总首页替代品。

#### Scenario: Dashboard concentrates the first decision context
- **WHEN** 已登录用户进入根路径 `/`
- **THEN** 前端默认首页流进入独立 Dashboard
- **AND** Dashboard 首屏优先回答“今天先看什么、哪些建议要处理、系统是否影响判断质量”
- **AND** 不要求用户先进入完整事件列表才能获得首页判断上下文

#### Scenario: Dashboard modules stay within the P0 boundary
- **WHEN** 产品或实现者定义 Dashboard 首版模块
- **THEN** Dashboard 包含重点事件、待处理审批摘要、关键健康提醒和主工作入口
- **AND** 不把完整事件列表、插件治理、审批执行动作或完整运行时排障台混入首页主流程

#### Scenario: Dashboard routes users into specialized workspaces
- **WHEN** 用户需要查看更多事件、处理审批或排查运行过程
- **THEN** Dashboard 提供进入 `/events`、`/approvals` 或运行态页面的稳定入口
- **AND** Dashboard 不在首页内复制这些页面的完整工作台能力

### Requirement: Events Serves as the Event Center

系统 SHALL 将 `/events` 定义为从 Dashboard 进入的事件中心页面，用于浏览、筛选和扩展重点事件视野，而不是承担系统总首页职责。

#### Scenario: Events extends the dashboard event workflow
- **WHEN** 用户从 Dashboard 或主导航进入 `/events`
- **THEN** 页面承接重点事件扩展浏览、筛选和排序
- **AND** 用户可以从重点事件区或事件列表稳定进入 `/events/:eventId`
- **AND** 页面不要求同时承担首页总控摘要职责

#### Scenario: Events keeps the event collection as the primary object
- **WHEN** 实现 `/events` 页面信息架构
- **THEN** 页面围绕事件集合组织筛选、排序、状态和空态
- **AND** 不把 ApprovalRequest、Plugin、Skill、Tool、Industry 或 Runtime 对象提升为页面主对象

#### Scenario: Events avoids approval and governance responsibilities
- **WHEN** 实现 `/events` 页面交互
- **THEN** 页面不内联 approve、reject、amend 或真实执行动作
- **AND** 页面不把插件、Skill、Tool、Industry 或 Runtime 调试对象抬成首屏主对象

### Requirement: Event Detail Prioritizes Analysis Before Approval

系统 SHALL 将 `/events/:eventId` 定义为围绕单条事件做事实、行业影响分析和最佳动作判断的决策页，并通过独立审批入口进入人工确认链路。

#### Scenario: Event detail emphasizes analysis first
- **WHEN** 用户进入 `/events/:eventId`
- **THEN** 页面先区分事件事实与行业影响分析
- **AND** 行业影响分析和最佳动作建议在首屏中具有高于运行摘要和审计入口的视觉优先级
- **AND** 用户可以解释“这条事件影响什么、系统建议什么、为什么建议这样做”

#### Scenario: Event detail separates decision evidence from runtime diagnostics
- **WHEN** 页面同时提供运行摘要、审计入口或系统过程线索
- **THEN** 这些信息用于辅助复核建议来源
- **AND** 不取代事件事实、行业影响分析和最佳动作建议的首屏判断位置
- **AND** 不展示完整模型推理链作为页面必备内容

#### Scenario: Event detail routes high-risk confirmation to approvals
- **WHEN** 页面展示最佳动作建议
- **THEN** 页面提供进入审批工作台或审批详情的入口
- **AND** 不在详情页直接完成批准或真实执行
- **AND** 支持观点、反方观点和关键不确定性保留在详情页语义中

#### Scenario: Event detail excludes related-history from the P0 contract
- **WHEN** 实现者为 V1 主链路定义 `/events/:eventId` 的必备内容
- **THEN** 相关历史事件展示不是 P0 必须能力
- **AND** 不因缺少相关历史事件而阻塞事件详情 / 决策页首版交付

### Requirement: Approvals Remains a Dedicated Human Confirmation Workspace

系统 SHALL 将 `/approvals` 定义为集中处理 ApprovalRequest 的独立工作台，并把批准语义与真实执行结果严格区分。

#### Scenario: Approvals centralizes human confirmation
- **WHEN** 用户进入 `/approvals`
- **THEN** 页面展示待处理审批请求及其风险、到期和确认等级摘要
- **AND** 用户可以在独立审批上下文中处理 approve、reject、request_reanalysis 或 amend
- **AND** 页面支持回到事件详情或审批详情复核证据

#### Scenario: Approvals keeps ApprovalRequest as the primary object
- **WHEN** 实现审批列表、审批详情或审批入口
- **THEN** 页面围绕 ApprovalRequest 的状态、风险、到期时间、确认等级和证据入口组织
- **AND** 不把事件列表、运行态调试或真实执行结果作为审批工作台主对象

#### Scenario: Approval wording does not imply execution
- **WHEN** 页面展示单条或批量审批动作
- **THEN** UI 语义明确批准只代表人工确认
- **AND** 不将批准文案写成已下单、已成交或已真实执行完成
- **AND** 批量处理必须比逐条处理更保守

### Requirement: P0 Mainflow Excludes Non-V1 Workspaces

系统 SHALL 明确 P0 主链路的首版非目标，避免后续实现把相关历史事件、独立健康治理、插件治理、API contract、generated client、数据模型或真实审批执行链路混入本 change 的页面契约。

#### Scenario: Related history does not block V1 event detail
- **WHEN** 实现者定义 `/events/:eventId` 的 P0 必备内容
- **THEN** 相关历史事件展示不是 P0 必须能力
- **AND** 不因缺少相关历史事件模块而阻塞事件详情 / 决策页首版交付

#### Scenario: Health reminders stay lightweight in dashboard
- **WHEN** Dashboard 展示系统健康信息
- **THEN** 信息仅用于提醒影响判断质量的关键状态
- **AND** 不要求在 P0 主链路中新增独立系统健康治理首页

#### Scenario: Governance and execution remain outside the P0 mainflow
- **WHEN** 实现 P0 主链路页面
- **THEN** 插件治理、完整运行时排障台、API contract、generated client、数据模型和真实审批执行链路不作为本 change 的首版页面能力
- **AND** 若后续需要实现这些能力，必须通过对应 issue、设计文档或 OpenSpec change 单独收口
