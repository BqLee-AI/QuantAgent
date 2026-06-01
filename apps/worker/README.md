# QuantAgent Worker

`apps/worker` 是 QuantAgent 后台消费侧的 composition root。它的职责很窄：读取 settings、组装 core runtime、启动 event bus consumer 和后续业务 handler。它不是事件协议定义层，也不是业务状态真源。

## 当前职责

- 读取 `quantagent.core.config.settings`
- 通过 `build_event_bus_runtime(...)` 组装 event bus runtime
- 作为 future Router / long-running handler 的启动入口

## 当前非目标

- 不定义 `EventEnvelope`
- 不定义 topic policy
- 不直接操作 Kafka client
- 不把 worker 逻辑塞进 API
- 不在这里实现 Router Agent / Decision / Industry Plugin 业务逻辑

## 当前代码入口

当前实现只有最小入口：

```python
from quantagent.worker.main import create_worker_app, create_worker_runtime, run
```

语义：

- `create_worker_runtime()`
  组装并返回 `EventBusRuntime`
- `create_worker_app()`
  组装 worker 的 session、captured-event handler 和 event bus runtime
- `run()`
  执行当前 V1 的一次 `source.event.captured` 订阅/消费流程；长期 loop 后续只扩展生命周期，不改变入口薄层职责

## 推荐扩展方式

后续如果要在 worker 里接入真实 handler，遵守这个形态：

```text
worker main
  -> load settings
  -> build_event_bus_runtime(...)
  -> create routing service / audit sink / domain handler(s)
  -> subscribe to topic(s)
  -> keep lifecycle / shutdown at worker boundary
```

不要在 worker 里做这些事：

- 手写 envelope encode / decode
- 手写 topic 校验
- 直接 import Kafka producer / consumer
- 把 DB / secret / event bus 暴露给插件

## 配置来源

worker 使用和 core 一致的 event bus 配置：

- `EVENT_BUS_BACKEND`
- `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS`
- `EVENT_BUS_KAFKA_CLIENT_ID`
- `EVENT_BUS_KAFKA_DEFAULT_GROUP_ID`
- `EVENT_BUS_TOPIC_PREFIX`

默认本地行为：

- `memory`
  不依赖 Kafka broker，适合最小启动和单元测试
- `kafka`
  需要显式配置 Kafka bootstrap servers

如果需要启用 Kafka backend，安装时要带上 Kafka extra：

```bash
uv sync --extra kafka --package quantagent-worker --package quantagent-core
```

## 本地验证

当前最小验证：

```bash
uv run --package quantagent-worker python -m unittest discover -s apps/worker/src/tests
```

当前测试验证 composition root 默认走 `memory` backend，以及 `run()` 会执行一次 `consume_once()` 并关闭 runtime。
