## ADDED Requirements

### Requirement: Agent audit UI MUST be shared across Events and Runtime

系统 SHALL 提供跨 `/events` 与 `/runtime` 复用的 Agent 审计展示边界，避免业务事件页直接依赖 runtime 私有组件或复制第二套 Agent 详情实现。

#### Scenario: Events and Runtime use shared Agent stage components
- **WHEN** `/events` 或 `/runtime` 需要展示 Router Agent stage、关键字段、完整结构化 JSON 或 trace refs
- **THEN** 前端 MUST 使用 `features/agent-audit/` 或等价共享 feature 边界中的展示组件
- **AND** `/events` MUST NOT 直接 import `features/runtime/components/agent/*` 作为长期实现
- **AND** `/runtime` MUST NOT 继续维护与 shared boundary 分叉的私有 Agent detail modal / JSON view / key fields 组件

#### Scenario: Shared component accepts stable display models
- **WHEN** shared Agent audit component 被调用
- **THEN** 它 MUST 接收稳定的 `AgentAuditSubject`、`AgentAuditStage`、trace refs 和 key fields 展示模型
- **AND** 它 MUST NOT 接收 `ApiResponse`、ORM objects、runtime 私有 DTO、provider raw response、完整 raw payload、plugin instances 或 secret-bearing runtime objects
- **AND** 各页面 MUST 在自己的 mapper 中把后端 DTO 转换为共享展示模型

### Requirement: Agent detail modal MUST show rich Agent output safely

系统 SHALL 通过独立 feature 组件弹窗展示每个 Agent stage 的详细输出，因为 Router Agent、未来行业 MainAgent 和其他处理阶段都可能有较大结构化内容。

#### Scenario: Router Agent detail modal shows auditable output
- **WHEN** 用户在 `/events` 或 `/runtime` 打开 Router Agent 详情
- **THEN** 弹窗 MUST 展示新闻标题、URL、source 摘要、content preview、stage 状态、处理摘要、关键字段、完整结构化 output JSON 和可审计 refs
- **AND** content preview MUST 是列表级或安全预览，不等同完整正文
- **AND** output JSON MUST 来自后端安全结构化 Agent output，而不是 provider raw response 或前端 mock

#### Scenario: Unsafe content is not rendered
- **WHEN** Agent detail modal 渲染 stage 输出
- **THEN** 它 MUST NOT 展示完整 chain-of-thought、provider raw response、完整 prompt、secret、完整正文、raw payload、ORM object、plugin instance 或连接串
- **AND** 不可用、缺失或被脱敏的字段 MUST 显示 explicit unavailable、masked 或 redacted 状态
- **AND** 它 MUST NOT 用 mock 内容补齐用户无权查看或后端未返回的字段

### Requirement: Shared Agent audit model MUST support future industry MainAgent stages

系统 SHALL 让 shared Agent audit 边界支持未来行业 MainAgent 处理结果，而不改变 `/events` 左侧列表主对象或 Runtime 排障职责。

#### Scenario: Future MainAgent stage can be appended
- **WHEN** 未来持久化行业 MainAgent 输出
- **THEN** `/events` MAY 将其作为同一新闻事件下的 additional Agent stage 展示
- **AND** `/runtime` MAY 将其作为排障 stage 展示
- **AND** 左侧列表主对象 MUST 仍是一篇已路由新闻事件，而不是 Agent message、tool call、topic 或 trace session

#### Scenario: Chat-style MainAgent output remains inside shared boundary
- **WHEN** 未来 MainAgent 输出 Markdown、消息流、toolcall、artifact 或 ChatAPP 形态内容
- **THEN** 这些渲染 MUST 扩展 shared Agent audit detail boundary
- **AND** 它 MUST NOT 被塞进 `/events` route 文件、runtime page 主体或 Router Agent 专属组件
- **AND** 它 MUST 继续遵守安全脱敏和 trace refs 边界

### Requirement: Runtime MUST remain diagnostics while sharing Agent audit components

系统 SHALL 保持 `/runtime` 为运行态排障入口，即使它复用了 Agent audit 组件展示真实 Router Agent output。

#### Scenario: Runtime shows why an event was not formed
- **WHEN** RawEvent 已采集但没有 routed read model、`industry.analysis.requested` 未消费、模型调用失败、schema validation failed、provider 未配置或 Kafka/worker/scheduler 异常
- **THEN** `/runtime` MUST 展示这些 captured、pending、failed 或 unavailable 事实
- **AND** 它 MUST 提供排障 trace、request、binding、run、model invocation 或 runtime health 线索
- **AND** 这些未形成 routed event 的新闻 MUST NOT 因为 runtime 可见而自动进入 `/events`

#### Scenario: Runtime does not become business event entry
- **WHEN** 用户需要浏览 AI 已筛选事件、Router decision、summary、relevance、target industry/topic 和业务详情
- **THEN** 正式业务入口 MUST 是 `/events`
- **AND** `/runtime` MAY 提供跳转到对应 `/events/{raw_event_id}` 的链接
- **AND** `/runtime` MUST NOT 复制 `/events` 的业务筛选、阅读顺序或 mock 业务结果

### Requirement: Shared Agent audit UI MUST include fixture-only test boundaries

系统 SHALL 允许 shared Agent audit 组件使用 fixture 进行单测和演示，但 production data path MUST 来自后端 read model。

#### Scenario: Fixture stays out of production route
- **WHEN** 正常应用运行并渲染 `/events` 或 `/runtime`
- **THEN** Agent audit stage 数据 MUST 来自对应 FeatureApi / TanStack Query 的后端响应
- **AND** fixture constructors MUST NOT 作为生产 query result 被调用
- **AND** fixture MAY 仅用于 unit tests、component tests、Playwright mock、debug/demo 或 harness

#### Scenario: Shared components expose clear README boundaries
- **WHEN** 新增 `features/agent-audit/` 或等价共享目录
- **THEN** 目录 MUST 包含 README 或 usage note
- **AND** README MUST 说明入口组件、展示模型、子目录职责、安全边界、不负责后端请求、不负责业务 API mapping、不负责 provider raw response 或 full article rendering
- **AND** 后续新增 MainAgent 渲染能力时 MUST 更新该 usage note
