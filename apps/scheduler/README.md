# QuantAgent Scheduler

`apps/scheduler` 是 QuantAgent 调度侧的 composition root。它负责组装 runtime、数据库 session、registry 与 core scheduling service，并驱动 `SourceBinding` interval loop；但不负责定义消息协议或把 event bus 直接暴露给插件。

## 当前职责

- 读取 `quantagent.core.config.settings`
- 通过 `build_event_bus_runtime(...)` 组装 event bus runtime
- 通过 `SourceBindingSchedulerLoopService` 扫描 due `SourceBinding`
- 调用 source runtime 并写入 `SchedulerRun` / `SourceBinding` 摘要
- 在成功抓到条目后发布 `source.event.captured`

## 当前非目标

- 不把 SourceBinding、retry policy、EventEnvelope 协议写死在入口层
- 不向插件暴露 event bus publisher
- 不在这里实现分布式锁、复杂 retry/backoff、RawEvent 持久化或 worker routing
- 不替代 `packages/core` 中的 binding/run service 与 loop orchestration

## 当前代码入口

当前实现提供两个入口：

```python
from quantagent.scheduler.main import create_scheduler_app, create_scheduler_runtime, run, run_once
```

语义：

- `create_scheduler_runtime()`
  组装并返回 `EventBusRuntime`
- `create_scheduler_app()`
  组装 registry、runtime、DB session 和 `SourceBindingSchedulerLoopService`
- `run_once()`
  执行一个固定 tick：扫描 due bindings、触发 source.fetch、记录 run、回写 `next_run_at`
- `run()`
  进入单进程固定轮询 loop，轮询间隔由共享 settings 控制

注意：

- `uv run api` 不会自动启动 scheduler
- scheduler 需要单独运行
- scheduler 依赖可用的 `DATABASE_URL`
- 如果用 Compose 跑 scheduler，默认会自动改用 `COMPOSE_DATABASE_URL`，不需要手工再写容器内数据库地址

## 推荐扩展方式

后续如果要接入真实调度链路，遵守这个形态：

```text
scheduler main
  -> load settings
  -> build_event_bus_runtime(...)
  -> build SourceBindingSchedulerLoopService
  -> call run_once / run_forever
  -> platform service constructs EventEnvelope
  -> publish through EventBusPublisher
```

不要在 scheduler 里做这些事：

- 直接把 publisher 传给插件
- 手写 source output -> envelope 映射
- 直接 import Kafka client
- 在入口层冻结业务 topic 之外的私有 topic 字符串
- 直接在入口层拼 ORM 查询、`next_run_at` 计算或 run 状态机

## 配置来源

scheduler 使用和 core 一致的 event bus 配置：

- `EVENT_BUS_BACKEND`
- `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS`
- `EVENT_BUS_KAFKA_CLIENT_ID`
- `EVENT_BUS_KAFKA_DEFAULT_GROUP_ID`
- `EVENT_BUS_TOPIC_PREFIX`
- `SCHEDULER_POLL_INTERVAL_SECONDS`
- `SCHEDULER_DUE_LIMIT`
- `SCHEDULER_RUN_TIMEOUT_MS`

默认本地行为：

- `memory`
  适合最小本地开发和无 Kafka 环境
- `kafka`
  需要显式配置 Kafka bootstrap servers

关键限制：

- `memory` backend 只适合当前进程内 smoke，不适合把事件跨进程传给 worker
- 如果 `scheduler` 和 `worker` 要分开进程完成主链路，必须改用 `kafka`

如果需要启用 Kafka backend，安装时要带上 Kafka extra：

```bash
uv sync --extra kafka --package quantagent-scheduler --package quantagent-core
```

## 本地验证

当前最小验证：

```bash
uv run --package quantagent-scheduler python -m unittest discover -s apps/scheduler/src/tests
```

当前测试验证：

- composition root 默认走 `memory` backend
- `run_once()` 会按 `SourceBinding` 扫描 due bindings
- 成功 run 会写 `SchedulerRun`、回写 `next_run_at` 并发布 `source.event.captured`

## 运行示例

单次调度 smoke：

```bash
DATABASE_URL='postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent' \
EVENT_BUS_BACKEND=memory \
uv run python -c 'import asyncio; from quantagent.scheduler.main import run_once; print(asyncio.run(run_once()))'
```

跨进程调度：

```bash
EVENT_BUS_BACKEND=kafka \
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
uv run quantagent-scheduler
```

明确边界：

- `#217` 只落地单进程 fixed tick + due binding 扫描
- `#221` 的 RawEvent 持久化/去重不在这里
- `#224` 的 worker binding/owner 路由不在这里
