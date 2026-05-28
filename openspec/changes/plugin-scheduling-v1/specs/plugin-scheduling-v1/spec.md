## ADDED Requirements

### Requirement: Scheduling V1 由平台触发插件能力

Plugin Scheduling V1 SHALL trigger plugin capabilities from the platform instead of letting plugins start their own loops.

#### Scenario: 手动 trigger 使用 Registry 和 Runtime
- **WHEN** 平台手动触发一个插件 capability
- **THEN** Scheduling 使用 Registry 中有效的 `PluginRecord`
- **AND** Scheduling 通过 Runtime V1 调用该 capability
- **AND** Scheduling 不通过硬编码 class、import 列表或 if/else 注册插件
- **AND** Scheduling 不要求插件自行读取数据库配置

#### Scenario: 插件不负责调度循环
- **WHEN** 插件实现 pull source 或 notification capability
- **THEN** 插件不得自行启动 while loop、长期后台线程或私有 ticker
- **AND** 插件只响应 Runtime invoke
- **AND** 调度频率、timeout、状态记录和后续重试策略由平台负责

### Requirement: Trigger request 有最小 JSON-safe contract

Plugin Scheduling V1 SHALL define a JSON-safe trigger request contract.

#### Scenario: trigger 输入包含调用目标和上下文
- **WHEN** 调度层构造一次插件调用
- **THEN** trigger request 包含 `plugin_id`
- **AND** trigger request 包含 `capability`
- **AND** trigger request 包含 `request_id`
- **AND** trigger request 包含 `trigger_type`
- **AND** trigger request 包含 `input`
- **AND** trigger request 包含 `effective_config`
- **AND** trigger request 包含 `metadata`
- **AND** trigger request 可以包含 `timeout_ms`

#### Scenario: trigger payload 必须 JSON-safe
- **WHEN** trigger request 包含 `input`、`effective_config` 或 `metadata`
- **THEN** 这些字段必须是 JSON-like object
- **AND** 值只能使用 JSON-safe 类型：string、number、boolean、null、array、object
- **AND** 不允许携带数据库 session、ORM model、内部 service、scheduler 或 secret resolver

### Requirement: 每次插件调用都有 run 记录

Plugin Scheduling V1 SHALL create an auditable run record for every triggered plugin invocation.

#### Scenario: run 记录包含最小审计字段
- **WHEN** Scheduling 创建一次 run
- **THEN** run 记录包含 `run_id`
- **AND** run 记录包含 `plugin_id`
- **AND** run 记录可以包含 `plugin_version`
- **AND** run 记录包含 `capability`
- **AND** run 记录包含 `request_id`
- **AND** run 记录包含 `trigger_type`
- **AND** run 记录包含 `status`
- **AND** run 记录包含 `started_at`、`finished_at` 和 `duration_ms`
- **AND** run 记录可以包含 `timeout_ms`
- **AND** run 记录包含 `output_summary`（可为空 object）和 `metadata`
- **AND** run 记录可以包含 `error_summary`

#### Scenario: run 状态有最小状态机
- **WHEN** 调度层处理一次 run
- **THEN** run 状态可以从 `queued` 进入 `running`
- **AND** run 终态可以是 `succeeded`
- **AND** run 终态可以是 `failed`
- **AND** run 终态可以是 `timeout`
- **AND** run 终态可以是 `cancelled`
- **AND** 终态必须记录 `finished_at` 和 `duration_ms`

### Requirement: 调度失败和 Runtime 错误保持结构化且脱敏

Plugin Scheduling V1 SHALL preserve structured Runtime errors and store sanitized run error summaries.

#### Scenario: Runtime 结构化失败进入 failed run
- **WHEN** Runtime V1 返回结构化错误
- **THEN** Scheduling 将 run 标记为 `failed`
- **AND** `error_summary` 包含错误 `code`、`message`、`stage`、`retryable` 和安全 `details`
- **AND** `error_summary` 不暴露 secret、token、cookie、原始 stack trace 或本地私有路径

#### Scenario: capability 不可用进入 failed run
- **WHEN** trigger request 指向插件 manifest 未声明的 capability
- **THEN** Scheduling 将 run 标记为 `failed`
- **AND** 错误 code 表示 capability 不可用
- **AND** 错误 stage 可以归因到 `invoke` 或 `schedule_precheck`

#### Scenario: timeout 进入 timeout run
- **WHEN** Runtime invoke 超过 trigger request 的 `timeout_ms`
- **THEN** Scheduling 将 run 标记为 `timeout`
- **AND** run 记录可以保存 `timeout_ms`
- **AND** `error_summary` 记录 timeout 语义
- **AND** run 记录包含 `finished_at` 和 `duration_ms`

### Requirement: 成功、空结果和后续链路保持分离

Plugin Scheduling V1 SHALL distinguish scheduling success from downstream persistence or event processing.

#### Scenario: Runtime 成功返回进入 succeeded run
- **WHEN** Runtime V1 成功返回 `PluginInvokeResult`
- **THEN** Scheduling 将 run 标记为 `succeeded`
- **AND** run 可以记录 `output_summary`
- **AND** Scheduling 成功不表示 RawEvent 已入库
- **AND** Scheduling 成功不表示 Event Bus 已发布

#### Scenario: 空结果不是失败
- **WHEN** source 插件成功执行但返回空 items
- **THEN** Scheduling 将 run 标记为 `succeeded`
- **AND** `output_summary` 可以表达空结果
- **AND** 调用方可以区分空结果、失败和 timeout

### Requirement: Interval 调度是 V1 边界但不要求完整分布式 scheduler

Plugin Scheduling V1 SHALL define a minimal interval scheduling boundary while deferring distributed scheduler implementation.

#### Scenario: interval policy 构造 interval trigger
- **WHEN** interval policy 到期
- **THEN** 平台可以构造 `trigger_type=interval` 的 trigger request
- **AND** interval trigger 复用同一个 Scheduling trigger service
- **AND** interval trigger 使用平台计算出的 effective config

#### Scenario: V1 不要求复杂调度能力
- **WHEN** 实现 Plugin Scheduling V1
- **THEN** 不要求实现分布式锁
- **AND** 不要求实现复杂 retry/backoff/rate limit/circuit breaker
- **AND** 不要求实现完整 SourceBinding 模型
- **AND** 不要求 API request 生命周期承担长期 scheduler loop
