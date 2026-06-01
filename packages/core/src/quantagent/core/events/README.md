# core events

`quantagent.core.events` 是 QuantAgent Event Bus V1 的共享基础设施边界。它的目标不是把业务流程塞进一个“总线工具箱”，而是统一消息 envelope、topic、backend、发布/订阅入口和平台侧转换边界，让 API、worker、scheduler 和后续 runtime service 能用同一套 contract 工作。

如果你只使用默认 `memory` backend，不需要 Kafka 客户端依赖；只有在启用 Kafka backend 时才需要安装 `quantagent-core[kafka]` 或等价 workspace extra。

## 职责

这个目录当前负责：

- 定义 `EventEnvelope`
- 定义默认 topic 集合与 `EventTopicPolicy`
- 定义 `EventBusPublisher`、`EventBusConsumer`、`EventBusHandler`
- 定义 `EventBusCodec`
- 提供 `InMemoryEventBus`
- 提供 `KafkaEventBusPublisher` 与 `KafkaEventBusConsumer`
- 提供 `EventBusSettings` 和 `build_event_bus_runtime(...)`
- 提供 `SourceEventPublisher`，把 `SourceFetchResult` 转成 `source.event.captured`

这个目录当前不负责：

- RawEvent / Event 数据库持久化
- dedupe、outbox、replay、DLQ 数据库记录
- FastAPI route、HTTP 状态码、前端 DTO
- 插件直接发布事件
- Router / Decision / Approval / Notification 业务逻辑

## 文件结构

```text
events/
  __init__.py
  README.md
  codec.py
  config.py
  envelope.py
  errors.py
  kafka.py
  memory.py
  ports.py
  service.py
  topics.py
```

职责划分：

- `envelope.py`
  只定义 envelope 字段和 JSON-safe 冻结边界。
- `topics.py`
  定义默认 topic 集合、schema version 和 topic 校验。
- `ports.py`
  定义发布/订阅/handler 接口，不暴露具体 backend。
- `codec.py`
  定义 encode / decode、敏感字段脱敏和错误摘要转换。
- `memory.py`
  提供本地默认 backend 和 contract test backend。
- `kafka.py`
  提供 Kafka producer / consumer adapter。
- `config.py`
  读取 event bus 相关配置。
- `service.py`
  提供 runtime builder 和平台侧发布 helper。

## 核心对象

### `EventEnvelope`

字段：

- `id`
- `topic`
- `payload`
- `producer`
- `created_at`
- `correlation_id`
- `causation_id`
- `headers`
- `retry_count`
- `schema_version`

设计约束：

- `payload` 和 `headers` 必须是 JSON-safe object。
- `schema_version` 当前固定从 `1` 开始。
- `id` 是消息 ID，不等于业务 Event ID。
- `correlation_id` 用于端到端链路，`causation_id` 用于表达直接上游动作或消息。

### `EventTopicPolicy`

默认 topic：

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

调用方不应自行拼接未知 topic。新增 topic 需要先更新 spec / design / issue 真源，再进实现。

### `EventBusSettings`

当前配置项：

- `EVENT_BUS_BACKEND`
  可选 `memory` 或 `kafka`，默认 `memory`
- `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS`
  Kafka broker 地址，只有 backend=`kafka` 时需要
- `EVENT_BUS_KAFKA_CLIENT_ID`
  Kafka client id
- `EVENT_BUS_KAFKA_DEFAULT_GROUP_ID`
  默认 consumer group id
- `EVENT_BUS_TOPIC_PREFIX`
  预留 topic prefix

## 默认使用方式

### 1. 组装 runtime

普通调用方不应该自己判断 backend 再去 new backend 对象，而是通过 `build_event_bus_runtime(...)` 统一组装：

```python
from quantagent.core.config import settings
from quantagent.core.events import EventBusSettings, build_event_bus_runtime

runtime = build_event_bus_runtime(EventBusSettings.from_settings(settings))
publisher = runtime.publisher
consumer = runtime.consumer
```

语义：

- `memory`
  适合本地开发、单元测试、无 Kafka 环境
- `kafka`
  适合跨进程 worker / scheduler / future runtime

Kafka backend 依赖说明：

```bash
uv sync --extra kafka --package quantagent-core
```

### 2. 发布普通事件

```python
from datetime import UTC, datetime

from quantagent.core.events import EventEnvelope

envelope = EventEnvelope(
    id="evt_123",
    topic="event.routed",
    payload={"event_id": "event-1", "industry_ids": ["semiconductor"]},
    producer="worker-router",
    created_at=datetime.now(UTC).isoformat(),
    correlation_id="req-1",
    causation_id="evt_122",
    headers={"request_id": "req-1"},
    retry_count=0,
)

await publisher.publish(envelope)
```

### 3. 把 source 结果发布成 captured 事件

如果你手上是 `SourceFetchResult`，优先走 `SourceEventPublisher`，不要在业务层重复手写 envelope 映射：

```python
from quantagent.core.events import SourceEventPublisher

source_publisher = SourceEventPublisher(publisher)

await source_publisher.publish_source_fetch_result(
    result,
    producer="plugin-scheduling",
    request_id="req-1",
    plugin_id="quantagent.official.source.placeholder",
    binding_id="binding-1",
)
```

它会：

- 固定 topic 为 `source.event.captured`
- 生成消息级 `id`
- 把 `SourceFetchResult` 转成标准 `payload`
- 补上 `binding_id`、`request_id`、`plugin_id`、`item_count` 等 payload/header 字段

## 订阅方式

consumer 侧只关心 topic、group 和 handler，不关心 Kafka client 细节：

```python
class RouteHandler:
    async def handle(self, envelope):
        ...

await consumer.subscribe(
    topics=("event.routed",),
    group_id="quantagent-worker",
    handler=RouteHandler(),
)
```

约束：

- handler 抛异常时，backend 会保留结构化失败，不把异常静默吞掉。
- worker / scheduler 入口只负责组装和启动，不定义 envelope 协议。

## 平台边界

### 插件不能直接发布事件

插件 RuntimeContext 不能暴露：

- `event_bus`
- publisher
- consumer
- DB session
- ORM model
- scheduler
- internal service
- secret resolver

正确路径是：

```text
PluginRuntimeService.invoke(...)
  -> typed output validation / normalization
  -> construct EventEnvelope
  -> EventBusPublisher.publish(...)
```

### Event Bus 不是状态真源

即使 backend 是 Kafka，也不能把它当业务状态恢复真源。当前状态真源仍然应该来自：

- 数据库
- REST 查询
- audit 记录

后续如果要引入 RawEvent 持久化、outbox、replay 或 DLQ 数据库存储，应该走新的 issue / OpenSpec，而不是往这个目录里直接堆逻辑。

## 敏感信息规则

`codec.py` 负责统一处理日志/错误摘要的脱敏。实现新逻辑时保持这些规则：

- 不输出 token、cookie、password、secret、api key
- 不输出完整本地私有路径
- 不在 diagnostics 中输出完整敏感 payload
- 不把原始异常文本直接原样写回客户端或日志

如果新增新的敏感 header / payload 字段，也要补到对应脱敏逻辑和测试里。

## 本地验证

当前最小验证入口：

```bash
uv run --package quantagent-core python -m unittest \
  packages.core.tests.test_event_bus_contract \
  packages.core.tests.test_event_bus_memory \
  packages.core.tests.test_event_bus_kafka \
  packages.core.tests.test_event_bus_service
```

如果还要连同 runtime / scheduling 回归一起跑：

```bash
uv run --package quantagent-core python -m unittest \
  packages.core.tests.test_event_bus_contract \
  packages.core.tests.test_event_bus_memory \
  packages.core.tests.test_event_bus_kafka \
  packages.core.tests.test_event_bus_service \
  packages.core.tests.test_runtime \
  packages.core.tests.test_scheduling
```
