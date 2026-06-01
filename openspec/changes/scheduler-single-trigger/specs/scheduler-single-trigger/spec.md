## ADDED Requirements

### Requirement: SchedulerRuntime 组装完整调度链路

`create_scheduler_runtime()` SHALL 返回一个 `SchedulerRuntime` dataclass，封装 `EventBusRuntime`、`PluginSchedulingService` 和 `PluginRegistry`。组装过程中 SHALL 将 `EventBusRuntime.publisher` 注入到 `PluginSchedulingService`，使调度结果能通过事件总线发布。

#### Scenario: 组装成功返回完整 SchedulerRuntime
- **WHEN** 调用 `create_scheduler_runtime()` 且 `EVENT_BUS_BACKEND=kafka` 且 Kafka bootstrap servers 已配置
- **THEN** 返回的 `SchedulerRuntime` 实例包含有效的 `event_bus`、`scheduling` 和 `registry`，且 `scheduling` 内部持有 publisher 引用

#### Scenario: 测试模式下使用 memory 后端
- **WHEN** 调用 `create_scheduler_runtime()` 且 `EVENT_BUS_BACKEND=memory`
- **THEN** 返回的 `SchedulerRuntime` 中 `event_bus.backend` 为 `"memory"`，`event_bus.publisher` 为 `InMemoryEventBus` 实例，且 `scheduling` 仍正常组装

### Requirement: run() 执行单次 source.fetch 触发

`run()` SHALL 通过 `SchedulerRuntime.scheduling.trigger()` 触发一次 `source.fetch` capability，目标插件由 `SCHEDULE_PLUGIN_ID` 环境变量控制（默认 `quantagent.official.source.placeholder`）。触发完成后 SHALL 输出结构化 JSON 日志并优雅退出。

#### Scenario: 默认插件触发成功
- **WHEN** 调用 `run()` 且未设置 `SCHEDULE_PLUGIN_ID` 且 placeholder-source 插件已安装且 Kafka 可用
- **THEN** scheduler 触发 `quantagent.official.source.placeholder` 的 `source.fetch`，事件发布到 Kafka，日志输出 `run_id`、`status=SUCCEEDED`、`duration_ms`、`plugin_id`，进程正常退出

#### Scenario: 自定义插件 ID 触发
- **WHEN** 设置 `SCHEDULE_PLUGIN_ID=quantagent.official.source.tavily` 且该插件已注册
- **THEN** scheduler 触发指定插件的 `source.fetch` 而非 placeholder

#### Scenario: 插件未找到时优雅失败
- **WHEN** `SCHEDULE_PLUGIN_ID` 指定的插件未在 registry 中注册
- **THEN** `trigger()` 返回 `PluginRunRecord`（status=FAILED），日志输出 `PLUGIN_NOT_FOUND` 错误信息，进程以非零退出码退出

#### Scenario: Kafka 配置缺失时启动失败
- **WHEN** `EVENT_BUS_BACKEND=kafka` 且 `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS` 为空
- **THEN** `create_scheduler_runtime()` 在 `build_event_bus_runtime()` 阶段抛出 `EventBusError`（code=`EVENT_BUS_KAFKA_CONFIG_MISSING`），进程以非零退出码退出

#### Scenario: Kafka broker 不可达时发布失败隔离
- **WHEN** `EVENT_BUS_BACKEND=kafka` 且配置完整但 broker 不可达，插件触发成功
- **THEN** `_maybe_publish_source_event()` 捕获 `EventBusError(EVENT_PUBLISH_FAILED)` 并输出 warning 日志，`PluginRunRecord.status` 仍为 `SUCCEEDED`，进程以退出码 0 退出

### Requirement: 事件总线后端策略——Kafka 为默认

Scheduler app SHALL 默认使用 Kafka 作为事件总线后端。`EVENT_BUS_BACKEND=memory` 仅用于单元测试场景，不作为运行时配置选项推荐给用户。当 `EVENT_BUS_BACKEND` 未设置时，MUST 默认为 `kafka`。

#### Scenario: 未设置 EVENT_BUS_BACKEND 时默认使用 Kafka
- **WHEN** 未设置 `EVENT_BUS_BACKEND` 环境变量
- **THEN** `create_scheduler_runtime()` 构建的 `EventBusRuntime.backend` 为 `"kafka"`

#### Scenario: 显式设置 memory 后端（测试用）
- **WHEN** 设置 `EVENT_BUS_BACKEND=memory`
- **THEN** `create_scheduler_runtime()` 构建的 `EventBusRuntime.backend` 为 `"memory"`，调度结果发布到 `InMemoryEventBus`

### Requirement: 结构化日志输出

`run()` 在触发完成后 SHALL 通过 `logging` 模块输出 INFO 级别日志，包含以下结构化字段：`run_id`、`status`、`duration_ms`、`plugin_id`、`capability`。

#### Scenario: 触发成功时日志输出
- **WHEN** 插件触发成功（status=SUCCEEDED）
- **THEN** 日志输出包含 `run_id`、`status=SUCCEEDED`、`duration_ms`（正整数）、`plugin_id`、`capability=source.fetch`

#### Scenario: 触发失败时日志输出
- **WHEN** 插件触发失败（status=FAILED）
- **THEN** 日志输出包含 `run_id`、`status=FAILED`、`error_summary`、`plugin_id`、`capability=source.fetch`

### Requirement: Kafka 后端组装与事件发布的单元测试

当 `EVENT_BUS_BACKEND=kafka` 时，MUST 有单元测试验证 `SchedulerRuntime` 正确组装了 `KafkaEventBusPublisher`，且调度结果能通过 publisher 发出事件。测试 SHALL 通过 mock 验证事件发布的正确性，不依赖真实 Kafka 实例。Mock 策略：mock `KafkaEventBusPublisher._get_producer` 返回 mock producer（避免 `AIOKafkaProducer.start()` 触发真实网络连接），或整体 mock `KafkaEventBusPublisher` 实例。

#### Scenario: Kafka 后端组装验证
- **WHEN** `create_scheduler_runtime()` 在 `EVENT_BUS_BACKEND=kafka` 且 `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092` 条件下执行
- **THEN** `SchedulerRuntime.event_bus.publisher` 为 `KafkaEventBusPublisher` 实例，`SchedulerRuntime.event_bus.consumer` 为 `KafkaEventBusConsumer` 实例

#### Scenario: Kafka 后端触发成功后事件发布验证
- **WHEN** `run()` 在 Kafka 后端模式下触发插件成功，且 mock 了 `KafkaEventBusPublisher.publish`
- **THEN** `publish` 被调用一次，传入的 `EventEnvelope.topic` 为 `source.event.captured`，`EventEnvelope.payload` 包含 `plugin_id` 和 `items`

#### Scenario: Kafka 配置缺失时启动失败验证
- **WHEN** `EVENT_BUS_BACKEND=kafka` 且 `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS` 为空
- **THEN** `create_scheduler_runtime()` 抛出 `EventBusError`（code=`EVENT_BUS_KAFKA_CONFIG_MISSING`）

### Requirement: Memory 后端单元测试

当 `EVENT_BUS_BACKEND=memory` 时，MUST 有单元测试验证 `SchedulerRuntime` 使用 `InMemoryEventBus`，且调度结果通过内存总线正确传递到已注册的 handler。

#### Scenario: Memory 后端组装验证（已有，保留）
- **WHEN** 调用 `create_scheduler_runtime()` 且 `EVENT_BUS_BACKEND=memory`
- **THEN** `SchedulerRuntime` 中 `event_bus.backend` 为 `"memory"`，`event_bus.publisher` 为 `InMemoryEventBus` 实例

#### Scenario: Memory 后端触发后事件到达 handler
- **WHEN** 在 memory 后端模式下触发插件成功，且已通过 `InMemoryEventBus.subscribe()` 注册了 handler
- **THEN** handler 收到 `source.event.captured` 事件，envelope payload 包含插件返回的 items

### Requirement: 优雅退出

`run()` 在调度完成后 SHALL 调用 `SchedulerRuntime.close()` 关闭 EventBusRuntime，释放 Kafka 连接等资源。无论触发成功或失败，MUST 执行清理。

#### Scenario: 触发成功后优雅退出
- **WHEN** 插件触发成功
- **THEN** 调用 `event_bus.close()` 释放资源，进程退出码为 0

#### Scenario: 触发失败后仍执行清理
- **WHEN** 插件触发失败或事件发布失败
- **THEN** 仍调用 `event_bus.close()` 释放资源，进程退出码为 1

### Requirement: Docker Compose scheduler 服务端到端验证

`docker-compose.yml` 中的 scheduler 服务 SHALL 显式配置事件总线环境变量，`depends_on` SHALL 依赖 Kafka 服务健康检查通过后才启动。通过 `docker compose --profile kafka up scheduler` 即可完成端到端验证。

#### Scenario: Docker Compose 启动 scheduler 并触发插件
- **WHEN** 执行 `docker compose --profile kafka up scheduler` 且 placeholder-source 已打包到镜像
- **THEN** scheduler 等待 Kafka 健康检查通过后启动，触发 `source.fetch`，事件发布到 Kafka，scheduler 以退出码 0 退出

#### Scenario: Docker Compose 中 Kafka 未就绪时 scheduler 等待
- **WHEN** `docker compose --profile kafka up scheduler` 但 Kafka healthcheck 未通过
- **THEN** scheduler 等待 Kafka 健康检查通过后再启动，不提前失败

#### Scenario: Docker Compose 移除 scheduler 对 db 的依赖
- **WHEN** 查看 `docker-compose.yml` 中 scheduler 服务的 `depends_on`
- **THEN** scheduler 不依赖 `db` 服务，只依赖 `kafka` 和可选的 `migrate`
