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
  组装 worker 的 session、captured-event handler、Readability enrichment seam、`industry.analysis.requested` topic publisher、AI intake handler、`event.routed` publisher 和 event bus runtime
- `run()`
  启动当前 V1 的常驻 consumer loop，持续消费 `source.event.captured` 与 `industry.analysis.requested`
- `run_once()`
  只执行一次单条拉取消费，用于 smoke / 测试，不作为默认本地运行方式

注意：

- `uv run api` 不会自动启动 worker
- worker 需要单独运行，推荐本地命令是 `uv run quantagent-worker`
- worker 依赖可用的 `DATABASE_URL`
- 如果用 Compose 跑 worker，默认会自动改用 `COMPOSE_DATABASE_URL`，不需要手工再写容器内数据库地址

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

关键限制：

- `memory` backend 只在当前进程内有效
- 如果 `scheduler` 和 `worker` 分开进程运行，`memory` backend 不会把 `source.event.captured` 从 scheduler 传给 worker
- 需要跨进程验证时，必须改用 `kafka`

如果需要启用 Kafka backend，安装时要带上 Kafka extra：

```bash
uv sync --extra kafka --package quantagent-worker --package quantagent-core
```

## 本地验证

当前最小验证：

```bash
uv run --package quantagent-worker python -m unittest discover -s apps/worker/src/tests
```

当前测试验证 composition root 默认走 `memory` backend，`run_once()` 保持单次 smoke 语义，`run()` 默认进入常驻消费并在关闭时回收 runtime。

当前主链路约束：

- worker 在消费 `source.event.captured` 后，可以通过受控 seam 调用 Readability 做正文增强
- 正文增强失败时允许 degraded 为 RSS 摘要，但必须保留结构化失败标记
- 半导体 owner 的成功 handoff 通过 `industry.analysis.requested` topic 表达，而不是在 worker 入口直接执行业务分析
- worker 在消费 `industry.analysis.requested` 后，会通过 `quantagent.core.event_intake` 的 single-call runner 产出 `event.routed`
- 默认本地 provider 是 review-only，不会裸连真实模型；要验证真实路由行为，优先在测试中注入 fake provider harness
- 若要让 AI intake 走真实模型，所选 provider / model 必须兼容 OpenAI-style `response_format={\"type\":\"json_object\"}` 结构化输出；不兼容时应预期只能看到连接成功，但 intake 运行阶段会失败或退回 review

AI intake 约束：

- 每篇 article item 最多一次 provider invocation
- 不允许 tool-call loop、multi-turn agent loop、二次网页抓取或模型分块总结
- `event.routed` 列表型输出不包含完整正文；完整正文只存在于 bounded context 内供一次 intake 判断使用

## 运行示例

单次消费 smoke：

```bash
DATABASE_URL='postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent' \
EVENT_BUS_BACKEND=memory \
uv run python -c 'import asyncio; from quantagent.worker.main import run_once; asyncio.run(run_once())'
```

跨进程消费：

```bash
EVENT_BUS_BACKEND=kafka \
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
uv run quantagent-worker
```
