## ADDED Requirements

### Requirement: Runtime 复用 Registry 记录加载插件

Plugin Runtime V1 SHALL use valid Plugin Registry records and manifest entrypoints as the only plugin loading source.

#### Scenario: 从有效 Registry 记录加载 entrypoint
- **WHEN** Runtime 准备加载插件
- **THEN** Runtime 使用 Registry 返回的有效 `PluginRecord`
- **AND** Runtime 读取该记录 manifest 中的 `entrypoint`
- **AND** Runtime 不重新扫描插件目录
- **AND** Runtime 不通过硬编码 class、import 列表或 if/else 注册插件

#### Scenario: entrypoint 每次调用产生独立插件实例
- **WHEN** Runtime 加载 manifest entrypoint
- **THEN** entrypoint 必须是插件 class 或 factory
- **AND** Runtime 每次调用都获得独立插件实例
- **AND** 预实例化 singleton 插件对象会被拒绝
- **AND** 并发调用不得共享同一个 RuntimeContext

#### Scenario: 无效 Registry 记录不会进入 runtime load
- **WHEN** 插件记录状态不是有效可加载状态
- **THEN** Runtime 拒绝加载该插件
- **AND** Runtime 返回结构化错误
- **AND** 错误 stage 表示加载前校验失败

### Requirement: Plugin SDK 提供协议和轻量基类

QuantAgent SHALL provide plugin author facing protocol types and an optional lightweight base class in `packages/plugin-sdk`.

#### Scenario: SDK 暴露 Runtime 协议类型
- **WHEN** 插件作者实现插件 entrypoint
- **THEN** SDK 提供 RuntimeContext、调用 request DTO、调用 result DTO、健康检查 result 和结构化错误类型
- **AND** 这些类型可被插件实现和 Runtime contract test 复用

#### Scenario: SDK 提供可选 BasePlugin
- **WHEN** 插件作者希望减少样板代码
- **THEN** SDK 提供轻量 `BasePlugin`
- **AND** `BasePlugin` 提供默认生命周期行为
- **AND** `BasePlugin` 可以保存 RuntimeContext 并提供受控 logger 访问
- **AND** `BasePlugin` 不包含数据库 session、scheduler、Event Bus publisher 或内部 service

#### Scenario: Runtime 不强制继承 BasePlugin
- **WHEN** 插件 entrypoint 返回的对象满足 Runtime 协议
- **THEN** Runtime 可以接受该插件对象
- **AND** Runtime 不要求该对象必须 `isinstance` 于具体 `BasePlugin`
- **AND** Runtime 仍然可以调用协议定义的生命周期和统一调用入口

### Requirement: RuntimeContext 是受控上下文

RuntimeContext SHALL expose only the minimal host-controlled information required for plugin execution.

#### Scenario: RuntimeContext 包含最小运行字段
- **WHEN** Runtime 创建 RuntimeContext
- **THEN** context 包含 plugin id
- **AND** context 包含 plugin version
- **AND** context 包含 request id
- **AND** context 包含受控 logger
- **AND** context 包含平台校验后的 config DTO 或 effective config
- **AND** context 可以包含运行模式和必要的只读运行元数据

#### Scenario: RuntimeContext 不作为服务定位器
- **WHEN** 插件接收 RuntimeContext
- **THEN** context 默认不暴露数据库 session
- **AND** context 默认不暴露 ORM model
- **AND** context 默认不暴露内部 service
- **AND** context 默认不暴露 scheduler
- **AND** context 默认不暴露 Event Bus publisher
- **AND** context 默认不暴露任意 secret resolver

### Requirement: 配置由平台校验并注入

Plugin Runtime V1 SHALL inject validated configuration into plugins instead of letting plugins discover platform configuration themselves.

#### Scenario: 插件接收已校验配置
- **WHEN** Runtime 调用插件生命周期或能力入口
- **THEN** Runtime 将平台根据 manifest config schema 校验后的配置作为 DTO 或 JSON-like object 传入插件
- **AND** 插件不需要自行读取用户输入
- **AND** 插件不需要自行读取数据库配置记录

#### Scenario: 插件不能绕过配置协议读取业务配置
- **WHEN** 插件需要用户业务配置或 secret-like 配置
- **THEN** 插件通过 Runtime 注入的 config DTO 获取
- **AND** 插件不得绕过平台配置协议直接读取数据库、内部 service 或未治理的本地私有配置

### Requirement: 生命周期由 Runtime 托管

Plugin Runtime V1 SHALL manage plugin lifecycle hooks and define their minimum semantics.

#### Scenario: Runtime 按顺序调用生命周期
- **WHEN** Runtime 启动一个插件实例
- **THEN** Runtime 调用 `load(context)`
- **AND** Runtime 在 load 成功后可以调用 `start()`
- **AND** Runtime 可以调用 `health_check()` 获取健康状态
- **AND** Runtime 在释放实例时调用 `stop()`

#### Scenario: 生命周期 hook 可以有默认行为
- **WHEN** 插件使用 SDK `BasePlugin`
- **THEN** `load` 可以保存 RuntimeContext
- **AND** `start` 和 `stop` 默认可以是 no-op
- **AND** `health_check` 默认可以返回健康或可用状态

#### Scenario: 插件不自行启动未托管后台循环
- **WHEN** 插件执行 `load` 或 `start`
- **THEN** 插件不得自行启动长期后台循环
- **AND** 插件不得自行启动未托管线程
- **AND** 插件不得自行实现独立 scheduler
- **AND** 需要调度的能力必须等待后续宿主调度边界接入

### Requirement: Runtime 提供统一调用入口

Plugin Runtime V1 SHALL call plugin capabilities through a unified structured request/result boundary.

#### Scenario: Runtime 通过统一 request 调用能力
- **WHEN** Runtime 调用插件能力
- **THEN** Runtime 传入包含 capability、request id、输入 DTO 和必要元数据的 request
- **AND** 插件返回 JSON-like 或 Pydantic-like result DTO
- **AND** result 可以被 API、worker 或测试 harness 序列化

#### Scenario: 插件 capability 不存在时返回结构化错误
- **WHEN** Runtime 请求插件不支持的 capability
- **THEN** Runtime 返回结构化错误
- **AND** 错误 code 表示 capability 不可用
- **AND** 错误 stage 为 `invoke`

### Requirement: Runtime 错误是结构化且脱敏的

Plugin Runtime V1 SHALL convert load, lifecycle and invoke failures into structured sanitized errors.

#### Scenario: entrypoint 加载失败返回结构化错误
- **WHEN** Runtime 无法加载 manifest entrypoint
- **THEN** Runtime 返回包含 code、message、stage、retryable 和 details 的错误
- **AND** stage 为 `load`
- **AND** 错误不暴露 stack trace 原文、secret、token、cookie 或本地私有路径

#### Scenario: 生命周期失败返回结构化错误
- **WHEN** `load`、`start`、`health_check` 或 `stop` 失败
- **THEN** Runtime 返回结构化错误
- **AND** stage 对应失败 hook
- **AND** retryable 根据失败类型由 Runtime 判断或由插件错误显式提供

#### Scenario: invoke 异常被 Runtime 包装
- **WHEN** 插件能力调用抛出异常或返回非法结果
- **THEN** Runtime 将失败转换为结构化错误
- **AND** stage 为 `invoke`
- **AND** details 只包含脱敏摘要和可诊断字段

### Requirement: Runtime V1 不扩大到调度、事件链路或真实执行

Plugin Runtime V1 SHALL keep execution scope limited to loading, context injection, lifecycle and unified invocation.

#### Scenario: Runtime V1 不实现调度链路
- **WHEN** 插件声明需要周期性执行
- **THEN** Runtime V1 不自行实现 SourceBinding
- **AND** Runtime V1 不自行实现 Scheduler loop
- **AND** Runtime V1 不自行发布 Event Bus
- **AND** Runtime V1 不自行写入 RawEvent

#### Scenario: Runtime V1 不实现真实交易执行
- **WHEN** 插件声明 executor-like capability
- **THEN** Runtime V1 不暴露 live trading
- **AND** Runtime V1 不调用 broker adapter
- **AND** Runtime V1 不绕过 Decision、Policy Gate 或 human approval

### Requirement: 单次调用失败与插件登记状态分离

Plugin Runtime V1 SHALL distinguish per-invocation failures from Registry record validity.

#### Scenario: 单次 invoke 失败不自动改写 Registry 状态
- **WHEN** 插件某次 invoke 失败
- **THEN** Runtime 返回该次调用的结构化错误
- **AND** Runtime 不默认把 Registry 插件记录改为 failed
- **AND** 后续状态变更必须有独立运行状态或审计策略支撑

#### Scenario: 持续不可加载可以进入运行失败状态
- **WHEN** 插件 entrypoint 持续不可加载或生命周期无法进入可用状态
- **THEN** Runtime 可以产生插件运行失败记录
- **AND** 该记录应保留 plugin id、version、stage、error code 和时间信息
- **AND** 该记录不得覆盖 Registry manifest 校验事实
