# QuantAgent Scheduler

`apps/scheduler` 是 QuantAgent 调度侧的 composition root。它负责组装完整调度链路（EventBusRuntime + PluginRegistry + PluginSchedulingService），触发一次 `source.fetch`，将结果通过事件总线发布，然后优雅退出。

## 当前职责

- 组装 `SchedulerRuntime`（封装 EventBusRuntime、PluginSchedulingService、PluginRegistry）
- 通过 `SCHEDULE_PLUGIN_ID` 环境变量指定触发哪个插件（默认 placeholder-source）
- 触发一次 `source.fetch`，结果发布到 Kafka（或 memory bus）
- 输出结构化 JSON 日志（run_id、status、duration_ms、plugin_id、capability）

## 当前非目标

- 不实现定时循环调度（interval loop）
- 不向插件暴露 event bus publisher
- 不处理非 `source.fetch` capability 的调度
- 不实现重试或失败补偿

## 代码入口

```python
from quantagent.scheduler.main import create_scheduler_runtime, run, SchedulerRuntime
```

语义：

- `SchedulerRuntime` — composition root dataclass，封装 event_bus、scheduling、registry
- `create_scheduler_runtime()` — 组装并返回 `SchedulerRuntime`
- `run()` — CLI 入口，触发一次 source.fetch 后退出

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SCHEDULE_PLUGIN_ID` | `quantagent.official.source.placeholder` | 要触发的插件完整 ID |
| `EVENT_BUS_BACKEND` | `kafka` | 事件总线后端（`kafka` 或 `memory`，memory 仅用于测试） |
| `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS` | — | Kafka broker 地址（kafka 后端时必填） |
| `EVENT_BUS_KAFKA_CLIENT_ID` | `quantagent-scheduler` | Kafka client ID |
| `EVENT_BUS_KAFKA_DEFAULT_GROUP_ID` | `quantagent-scheduler` | Kafka consumer group ID |
| `EVENT_BUS_TOPIC_PREFIX` | — | 事件 topic 前缀 |

> **注意**: scheduler 的 `EVENT_BUS_BACKEND` 默认为 `kafka`（通过 `os.environ.get` 覆盖），不修改 `packages/core` 的 `Settings` 全局默认值（保持 `memory`）。

## Docker Compose 验证

```bash
# 端到端验证（需要 Kafka profile）
docker compose --profile kafka up scheduler

# 指定自定义插件
SCHEDULE_PLUGIN_ID=quantagent.official.source.tavily docker compose --profile kafka up scheduler
```

## 本地验证（memory 后端，无需 Kafka）

```bash
EVENT_BUS_BACKEND=memory quantagent-scheduler
```

## 单元测试

```bash
uv run --package quantagent-scheduler python -m unittest discover -s apps/scheduler/src/tests
```

测试覆盖：
- memory 后端组装与事件发布
- Kafka 后端组装（mock）
- Kafka 发布失败隔离
- 插件未找到优雅失败
- 结构化日志输出
