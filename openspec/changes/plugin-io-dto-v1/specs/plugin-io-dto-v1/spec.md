## ADDED Requirements

### Requirement: Plugin IO DTO V1 在 Runtime transport 之上定义 typed contract

Plugin IO DTO V1 SHALL define capability-specific typed DTO without replacing the existing Runtime V1 invoke transport.

#### Scenario: Runtime transport 保持通用壳子
- **WHEN** 平台调用插件 capability
- **THEN** Runtime 继续使用统一 `PluginInvokeRequest` / `PluginInvokeResult` transport
- **AND** capability-specific typed DTO 作为 `input` / `output` 的语义真源
- **AND** Runtime 不需要因为本 change 改为 capability-aware 生命周期或加载逻辑

#### Scenario: `PluginInput` 与 `PluginResult` 是 typed payload 抽象
- **WHEN** OpenSpec 或 SDK 文档提到 `PluginInput` / `PluginResult`
- **THEN** 它们表示 capability-specific typed payload 的抽象边界
- **AND** `PluginInput` 映射到 Runtime V1 request 的 `input`
- **AND** `PluginResult` 映射到 Runtime V1 result 的 `output`
- **AND** 它们不新增第二套 runtime transport

#### Scenario: typed DTO 不直接等同 core 内部对象
- **WHEN** 插件返回 typed output DTO
- **THEN** DTO 表达 draft / result
- **AND** DTO 不直接等同 ORM model、数据库对象或 core 内部 service 对象
- **AND** core 后续负责将 DTO 转换为内部对象或后续链路输入

### Requirement: DTO 保持稳定字段、只读语义和默认 dataclass 实现

QuantAgent SHALL keep Plugin IO DTO V1 behavior stable while allowing the implementation to follow the existing plugin-sdk frozen dataclass style.

#### Scenario: typed DTO 与 Runtime DTO 风格一致
- **WHEN** plugin-sdk 暴露 `source.fetch` 或 `notification.send` typed DTO
- **THEN** DTO 默认使用冻结 dataclass 或等价只读对象风格
- **AND** DTO 字段在运行时不可被调用方直接就地修改
- **AND** DTO contract 以字段语义、校验、序列化和只读行为为准
- **AND** DTO 不要求本轮切换到另一套唯一模型系统

### Requirement: DTO 必须可校验

Plugin IO DTO V1 SHALL support validation of required fields, basic field types and JSON-safe values.

#### Scenario: DTO 校验缺失或非法字段
- **WHEN** 调用方构造 typed input/output DTO
- **THEN** DTO 或配套 helper 可以校验必填字段是否存在
- **AND** DTO 或配套 helper 可以校验基础字段类型
- **AND** DTO 或配套 helper 可以拒绝不可序列化对象

#### Scenario: DTO 校验失败进入结构化错误边界
- **WHEN** typed DTO 校验失败发生在插件调用边界
- **THEN** 失败应转换为 Runtime V1 结构化错误
- **AND** 错误 stage 可以归因到 `invoke` 或 `config`
- **AND** 错误不得泄露 secret、token、cookie 或本地私有路径

### Requirement: `source.fetch` 有第一版 typed input/output

Plugin IO DTO V1 SHALL define a first-pass typed contract for `source.fetch`.

#### Scenario: source fetch 输入有统一 typed DTO
- **WHEN** 平台或测试 harness 构造一次 `source.fetch` 调用
- **THEN** 可以使用 `SourceFetchInput` 表达 capability-specific 输入
- **AND** 该输入可映射到 Runtime V1 通用 invoke request 的 `input`
- **AND** 输入支持 `query`、`limit`、`cursor` 和 `metadata`
- **AND** `metadata` 必须是 JSON-like object，且值只能使用 JSON-safe 类型：string、number、boolean、null、array、object

#### Scenario: source fetch 输出使用 `SourceItemDraft`
- **WHEN** source 插件成功返回抓取结果
- **THEN** 结果使用 `SourceFetchResult`
- **AND** `SourceFetchResult` 包含 `items`
- **AND** `SourceFetchResult` 可以包含 `next_cursor`
- **AND** `SourceFetchResult` 包含 `metadata`
- **AND** `SourceFetchResult.metadata` 必须是 JSON-like object，且值只能使用 JSON-safe 类型：string、number、boolean、null、array、object
- **AND** 单条产物使用中性的 `SourceItemDraft`
- **AND** `SourceItemDraft` 不直接命名为 `RawEventDraft`
- **AND** `SourceItemDraft` 不直接命名为 `EventDraft`
- **AND** `SourceItemDraft` 支持 `external_id`、`url`、`title`、`content`、`author`、`published_at`、`captured_at`、`raw_payload` 和 `metadata`

#### Scenario: source fetch 可以表达空结果
- **WHEN** source 插件成功执行但没有抓到可输出项目
- **THEN** `SourceFetchResult` 仍然可以表达成功状态
- **AND** 结果可以包含空 items 集合
- **AND** 调用方可以区分“空结果”与“执行失败”

### Requirement: `notification.send` 有第一版 typed input/output

Plugin IO DTO V1 SHALL define a first-pass typed contract for `notification.send`.

#### Scenario: notification send 输入覆盖文本消息与最小通道字段
- **WHEN** 平台或测试 harness 构造一次 `notification.send` 调用
- **THEN** 可以使用 `NotificationSendInput` 表达 capability-specific 输入
- **AND** 输入至少支持文本消息
- **AND** 输入至少支持 `channel`
- **AND** 输入至少支持 `severity`
- **AND** 输入可以支持 `recipient`
- **AND** 输入可以携带必要 `metadata`
- **AND** `metadata` 必须是 JSON-like object，且值只能使用 JSON-safe 类型：string、number、boolean、null、array、object

#### Scenario: notification send 输出表达发送结果
- **WHEN** notification 插件完成发送尝试
- **THEN** 结果使用 `NotificationSendResult`
- **AND** 结果包含 `accepted`
- **AND** 结果可以包含 `provider_message_id`
- **AND** 结果包含 `retryable`
- **AND** 结果包含 `metadata`
- **AND** `metadata` 必须是 JSON-like object，且值只能使用 JSON-safe 类型：string、number、boolean、null、array、object
- **AND** 结果适合被审计记录、测试 harness 或后续日志层消费

#### Scenario: notification send 失败语义分层
- **WHEN** notification provider 明确拒收、限流或临时不可投递
- **THEN** 插件可以返回 `NotificationSendResult(accepted=false)`
- **AND** `retryable` 表示该发送结果是否建议重试
- **WHEN** 插件配置缺失、payload 校验失败、插件异常或 runtime 失败
- **THEN** 失败通过 Runtime V1 结构化错误表达
- **AND** 不通过 `NotificationSendResult` 平行表达 runtime error

### Requirement: 插件输出必须可序列化、可审计

Plugin IO DTO V1 SHALL be serializable, auditable, and compatible with API / worker / test harness usage.

#### Scenario: typed DTO 可以被序列化
- **WHEN** 调用方消费 typed input/output DTO
- **THEN** DTO 可以转换为 JSON-like 数据结构
- **AND** DTO 不依赖不可序列化对象
- **AND** DTO 不要求消费者持有插件私有 Python 类型才能理解字段

#### Scenario: 输出不得泄露受控对象或敏感信息
- **WHEN** 插件构造 typed output DTO
- **THEN** DTO 不直接暴露数据库 session、ORM model、内部 service 或其他宿主内部对象
- **AND** DTO 不应泄露 secret、token、cookie 或本地私有路径

### Requirement: 错误继续沿用 Runtime V1 结构化边界

Plugin IO DTO V1 SHALL reuse the existing structured Runtime V1 error shape instead of inventing a second error protocol.

#### Scenario: source 或 notification 调用失败仍返回结构化错误
- **WHEN** `source.fetch` 或 `notification.send` 调用失败
- **THEN** 失败仍通过现有结构化错误字段表达
- **AND** 错误包含 `code`、`message`、`stage`、`retryable` 和 `details`
- **AND** typed DTO 不要求额外定义平行的 capability-specific error envelope

#### Scenario: DTO 场景可区分失败与空结果
- **WHEN** 调用方查看 `source.fetch` 或 `notification.send` 的结果
- **THEN** 调用方可以区分结构化失败
- **AND** 调用方可以区分成功但空结果
- **AND** 调用方可以区分成功且有结果
