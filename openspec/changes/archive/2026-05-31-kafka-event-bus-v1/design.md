## Context

QuantAgent 的主链路已经在 PRD 和设计文档中确定为事件驱动：Source Plugin 产出标准 source output，平台转换为 RawEvent / Event 后进入 Event Bus，再由 Router Agent、Industry Plugin / AgentRuntime、Scoring、Decision / Policy Gate、Notification / Approval / Broker、Persistence / Audit 和 WebSocket 继续处理。当前 Plugin Runtime、Plugin IO DTO 和 Plugin Scheduling 已经分别收住插件调用、typed output 和 run 状态，但 Scheduling 成功仍不代表 RawEvent 已入库或 Event Bus 已发布。

现有 `docs/design/01-tech-stack-and-project-structure.md` 与 `docs/design/10-deployment-and-runtime-design.md` 仍写“初版 Event Bus 进程内实现，后续 Redis”。issue #193 和本 change 将这条路线调整为：V1 默认提供内存 fake，Kafka 是显式启用的运行时 adapter。OpenSpec 先固定该架构边界，后续实现 PR 再回写设计文档。

## Goals / Non-Goals

**Goals:**

- 定义 Event Bus V1 的核心 contract：`EventEnvelope`、topic policy、publisher / consumer port、handler registry、codec、内存 fake 和 Kafka adapter。
- 让 API、worker、scheduler、future router / agent runtime 等调用方只依赖 `packages/core` 的 event bus port，不直接耦合 Kafka client。
- 让测试和普通本地开发在无 Kafka 时可运行；Kafka 通过 Compose profile 或显式环境变量启用。
- 固定插件隔离：Plugin SDK / RuntimeContext 不暴露 Event Bus publisher，插件输出必须由平台 service 转换后发布。
- 固定 Event Bus 与持久化 / audit 的边界：消息队列负责异步分发，不替代数据库和审计真源。

**Non-Goals:**

- 不实现 RawEvent / Event 数据库持久化、dedupe、outbox、replay 或 DLQ 数据库记录。
- 不实现 Router Agent、Industry Plugin 分析、Decision / Policy Gate、Approval、Notification、Broker 或 WebSocket 实时推送。
- 不新增 REST API 或 Web UI。
- 不让 FastAPI router 承担长期 consumer loop。
- 不在 OpenSpec 中钉死具体 Python Kafka 客户端；实现 PR 需要基于 lockfile、维护状态和官方文档再确认。

## Decisions

### 1. Event Bus 进入 `packages/core` 共享基础设施边界

后续实现应落在 `packages/core/src/quantagent/core/events/` 或等价目录。建议目录蓝图：

```text
packages/core/src/quantagent/core/events/
  __init__.py
  envelope.py
  topics.py
  ports.py
  codec.py
  errors.py
  memory.py
  kafka.py
  config.py
  README.md

packages/core/tests/test_event_bus_contract.py
packages/core/tests/test_event_bus_memory.py
packages/core/tests/test_event_bus_kafka.py
```

职责划分：

- `envelope.py`：定义 `EventEnvelope`，只表达消息 envelope，不直接复用 ORM model、API DTO 或 Plugin DTO。
- `topics.py`：定义 V1 topic 常量、命名校验和 schema version 约束。
- `ports.py`：定义 `EventBusPublisher`、`EventBusConsumer`、`EventBusHandler` 等 Protocol / 抽象接口。
- `codec.py`：负责 envelope 与 JSON-safe bytes / mapping 之间的 encode / decode，并集中做脱敏边界。
- `memory.py`：提供内存 fake，用于单元测试和普通本地开发。
- `kafka.py`：提供 Kafka adapter，实现 producer / consumer、consumer group、ack / commit、shutdown 和 readiness。
- `config.py`：从环境变量或 settings 读取 event bus backend、Kafka bootstrap servers、topic prefix、consumer group 等配置。
- `README.md`：说明哪些模块可以调用 event bus port、哪些对象不能放入 envelope、为什么插件不能直接拿 publisher。

选择 `packages/core` 的原因是 Event Bus 会被 API、worker、scheduler、agent、plugin runtime 周边服务复用；`packages/core` 已是共享基础设施包且禁止反向依赖 app / web / 具体插件。Kafka adapter 暂不放入 `packages/adapters`，因为 V1 需要先稳定 core runtime 基础能力，拆到 adapters 会让实现者在 core port 和官方 adapter package 之间多做一次不必要的依赖决策。

### 2. Envelope 使用稳定 JSON-safe contract

V1 envelope 固定为：

```text
EventEnvelope
  id: string
  topic: string
  payload: object
  producer: string
  created_at: string
  correlation_id: string | null
  causation_id: string | null
  headers: object
  retry_count: integer
  schema_version: integer
```

字段约束：

- `id` 是消息级唯一 ID，不等同于业务 Event ID。
- `topic` 必须通过 topic policy 校验。
- `payload`、`headers` 必须是 JSON-like object，只允许 string、number、boolean、null、array、object。
- `created_at` 使用可序列化 UTC 时间字符串。
- `correlation_id` 表示一次端到端链路，`causation_id` 表示直接上游消息或动作。
- `producer` 使用稳定模块名，例如 `plugin-scheduling`、`source-ingestion`、`worker-router`。
- `retry_count` 只表达消息处理尝试次数，不承诺完整 retry scheduler。
- `schema_version` 从 1 开始，后续 schema 破坏性变化必须另开 OpenSpec。

V1 不把 `Event` 对象整体作为 envelope 根字段，而是使用 `payload` 承载业务内容。原因是 Event Bus 是跨阶段分发协议，既会承载 source captured，也会承载 routing / decision / runtime failed 这类非裸 Event payload。

### 3. Topic policy 沿用现有设计草案

V1 默认 topic 集合：

```text
source.event.captured
event.routed
industry.analysis.requested
industry.analysis.completed
analysis.scored
decision.created
approval.requested
approval.completed
notification.requested
notification.completed
broker.dry_run_requested
broker.dry_run_completed
runtime.failed
```

topic policy 只允许已登记 topic 或后续明确扩展的 namespaced topic。实现不得让调用方随意拼接未知 topic。后续如需增加 topic，必须通过 OpenSpec、issue 或设计文档真源补充。

### 4. 默认内存 fake，Kafka 显式启用

Event Bus backend 默认为内存 fake，适用于单元测试和普通本地开发。Kafka 通过显式环境变量或 Compose profile 启用，示例配置项建议为：

```text
EVENT_BUS_BACKEND=memory | kafka
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
EVENT_BUS_KAFKA_CLIENT_ID=quantagent-local
EVENT_BUS_KAFKA_DEFAULT_GROUP_ID=quantagent-worker
EVENT_BUS_TOPIC_PREFIX=
```

这些名称是实现蓝图，最终实现可以按现有 settings 风格调整，但必须保留环境变量覆盖入口。没有 Kafka 配置时，应用应能用内存 backend 最小启动；只有显式选择 `EVENT_BUS_BACKEND=kafka` 时才要求 Kafka 配置可用。

### 5. Publisher / consumer port 隔离 Kafka 细节

核心接口固定为：

```text
EventBusPublisher.publish(envelope)
EventBusConsumer.subscribe(topics, group_id, handler)
EventBusHandler.handle(envelope)
EventBusCodec.encode(envelope)
EventBusCodec.decode(message)
EventTopicPolicy.validate(topic)
```

接口语义：

- `publish` 接收完整 `EventEnvelope`，负责校验 topic、JSON-safe payload 和脱敏边界。
- `subscribe` 接收 topic 列表、consumer group 和 handler；consumer group 对内存 fake 可为测试命名，对 Kafka adapter 映射到 Kafka consumer group。
- `handler.handle` 抛出的异常不能吞掉，adapter 需要转成结构化失败，便于测试和后续 DLQ / audit 接入。
- `codec` 集中处理 encode / decode，避免 Kafka adapter、memory fake 和 future tests 各自手写 wire shape。

### 6. Kafka adapter 只实现最小运行时语义

Kafka adapter V1 需要表达：

- producer publish。
- consumer subscribe。
- consumer group。
- handler 成功后 ack / commit。
- handler 失败时不伪装成功，并保留失败摘要。
- graceful shutdown。
- readiness / health check helper。

Kafka adapter V1 不要求实现复杂 retry/backoff、DLQ topic、exactly-once、transactional producer、schema registry、outbox replay 或跨语言 contract generation。这些能力必须拆后续 issue。

### 7. 插件不能直接发布事件

Plugin RuntimeContext 不得暴露 `event_bus`、publisher、consumer、DB session、scheduler、internal service 或 secret resolver。source 插件只返回 `SourceFetchResult` / `SourceItemDraft` 或等价 typed output。平台 service 在 Runtime invoke 成功后负责：

```text
PluginSchedulingService / future SourceIngestionService
  -> PluginRuntimeService.invoke(...)
  -> typed output validation / normalization
  -> construct EventEnvelope
  -> EventBusPublisher.publish(envelope)
```

这条边界防止插件绕过配置、审计、权限和事件协议治理。

### 8. Worker / scheduler / API 的接入边界

- `apps/worker` 后续可以作为 consumer / handler composition root，启动 Router 或长耗时处理，但不定义 envelope 或 topic 协议。
- `apps/scheduler` 后续可以触发 plugin scheduling 并由平台 service 发布事件，但不直接把 SourceBinding / EventEnvelope 协议写死在入口里。
- `apps/api` 可以提供管理 API 或健康检查，但不启动长期 consumer loop，不承担 worker 语义。
- WebSocket / realtime 后续只能消费状态变化提醒，不作为业务状态真源。

### 9. 持久化和 audit 暂不进入 V1 实现范围

Event Bus V1 不承诺消息持久化等于业务持久化。即使 Kafka 保存消息，业务状态恢复仍必须以后续数据库、REST 和 audit record 为真源。RawEvent 入库、Event 状态迁移、dedupe、outbox、replay、DLQ 数据库记录属于后续 issue。

## Risks / Trade-offs

- [风险] Kafka adapter 放在 `packages/core` 会增加 core 的可选依赖重量。  
  缓解：Kafka 依赖必须作为显式 backend 启用；测试和普通本地开发默认 memory，不因 Kafka 缺失阻塞最小能力。

- [风险] 只做内存 fake + Kafka adapter，不做 outbox，无法证明 DB 写入和消息发布一致性。  
  缓解：本 change 明确不做 RawEvent 持久化和 outbox；实现 PR 不得把 Event Bus 误写成状态真源，后续用独立 issue 收一致性问题。

- [风险] topic 集合过早冻结会限制后续业务。  
  缓解：V1 只固定当前设计文档已有主链路 topic；新增 topic 必须有 OpenSpec / issue 真源，避免临时字符串扩散。

- [风险] Kafka 客户端选型错误会带来维护成本。  
  缓解：OpenSpec 不钉死具体库；实现前查 lockfile、已安装版本、官方文档和维护状态，并在 PR 说明取舍。

- [风险] 插件作者可能尝试直接发布事件以减少平台 glue code。  
  缓解：spec 和 README 必须明确 RuntimeContext 禁止暴露 publisher，contract tests 保持 forbidden host object 检查。

## Migration Plan

1. 先提交 OpenSpec-only PR，只包含 `openspec/changes/kafka-event-bus-v1/**`。
2. 维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。
3. 实现 PR 先落 `packages/core` event bus model / port / memory fake / tests，再落 Kafka adapter 和可选 Compose profile。
4. 实现 PR 或后续文档 PR 回写 `docs/design/01`、`docs/design/02`、`docs/design/10`，说明 Kafka 取代 Redis 演进路线。
5. 如实现中发现必须引入 RawEvent 持久化、outbox、DLQ 数据库记录或 replay，停止扩大范围，另开 issue / OpenSpec。

## Open Questions

- 具体 Python Kafka 客户端选型留到实现 PR 前确认。
- Kafka topic 是否需要统一 prefix 默认值，留到实现时结合部署配置确认；V1 只要求支持可配置 prefix。
- DLQ 是 Kafka topic 还是数据库失败记录，留给后续 issue；V1 只保留失败摘要和扩展点。
