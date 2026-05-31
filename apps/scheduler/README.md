# QuantAgent Scheduler

`apps/scheduler` 是 QuantAgent 调度侧的 composition root。它负责组装 runtime 并触发后续 scheduling / source ingestion 流程，但不负责定义消息协议或把 event bus 直接暴露给插件。

## 当前职责

- 读取 `quantagent.core.config.settings`
- 通过 `build_event_bus_runtime(...)` 组装 event bus runtime
- 为 future scheduling loop / trigger orchestration 提供启动入口

## 当前非目标

- 不把 SourceBinding、retry policy、EventEnvelope 协议写死在入口层
- 不向插件暴露 event bus publisher
- 不在这里补完整长期调度循环
- 不替代 `PluginSchedulingService`

## 当前代码入口

当前实现只有最小入口：

```python
from quantagent.scheduler.main import create_scheduler_runtime, run
```

语义：

- `create_scheduler_runtime()`
  组装并返回 `EventBusRuntime`
- `run()`
  固定 scheduler 的 composition root；当前不启动完整长期调度循环

## 推荐扩展方式

后续如果要接入真实调度链路，遵守这个形态：

```text
scheduler main
  -> load settings
  -> build_event_bus_runtime(...)
  -> call PluginSchedulingService / SourceIngestionService
  -> platform service constructs EventEnvelope
  -> publish through EventBusPublisher
```

不要在 scheduler 里做这些事：

- 直接把 publisher 传给插件
- 手写 source output -> envelope 映射
- 直接 import Kafka client
- 在入口层冻结业务 topic 之外的私有 topic 字符串

## 配置来源

scheduler 使用和 core 一致的 event bus 配置：

- `EVENT_BUS_BACKEND`
- `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS`
- `EVENT_BUS_KAFKA_CLIENT_ID`
- `EVENT_BUS_KAFKA_DEFAULT_GROUP_ID`
- `EVENT_BUS_TOPIC_PREFIX`

默认本地行为：

- `memory`
  适合最小本地开发和无 Kafka 环境
- `kafka`
  需要显式配置 Kafka bootstrap servers

如果需要启用 Kafka backend，安装时要带上 Kafka extra：

```bash
uv sync --extra kafka --package quantagent-scheduler --package quantagent-core
```

## 本地验证

当前最小验证：

```bash
uv run --package quantagent-scheduler python -m unittest discover -s apps/scheduler/src/tests
```

当前测试只验证 composition root 默认走 `memory` backend，不验证完整长期调度 loop。
