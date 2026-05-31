## Context

当前仓库已经有这些可复用能力：

- `RegistryScanner` / `PluginRegistry` 能发现官方插件。
- `plugins/sources/placeholder-source/` 提供最小可运行 `source.fetch` 官方插件。
- `PluginSchedulingService.trigger()` 能通过 runtime 调度 source plugin。
- `scheduling-event-bus-bridge-v1` 已经把成功的 `source.fetch` 输出桥接为 `source.event.captured`。
- `InMemoryEventBus` 和 `SourceEventPublisher` 已经可在不依赖 Kafka 的情况下完成发布/订阅。

缺的不是底层能力，而是一个最小演示入口，把这些已有点串成一条可直观看见的线，并证明：

```text
plugin -> scheduling -> event bus -> consumer
```

因此，本 change 只定义一个 CLI demo，而不是扩展系统业务能力。

## Goals / Non-Goals

**Goals:**

- 定义 `quantagent-demo` CLI 的最小行为和输出。
- 固定演示链路为：插件扫描 -> `source.fetch` 触发 -> `source.event.captured` 发布 -> fake consumer 收到事件。
- 固定使用 `placeholder-source` 作为演示插件。
- 固定使用 `InMemoryEventBus` 作为事件总线实现。
- 固定输出为人类可读日志，方便维护者一眼确认链路已连通。

**Non-Goals:**

- 不扩展成 analysis / strategy / discord / approval / broker 主链演示。
- 不增加 Kafka、DB、worker loop、scheduler loop 或外部服务依赖。
- 不定义新的 Event Bus 契约、新主题或新 plugin capability。
- 不改 `placeholder-source` 的现有能力边界。
- 不在本轮引入面向机器消费的复杂 JSON 输出协议。

## Decisions

### Decision 1: CLI 只证明最小 source 事件闭环

CLI 只收住：

```text
scan placeholder plugin
-> trigger source.fetch
-> publish source.event.captured
-> fake consumer receive
```

原因：

- `#205` 当前真正需要证明的是“插件的东西能够合理送到消息队列里，并且 fake consumer 能收到”。
- 继续把 analysis / strategy / approval / broker 混进来，会把 demo 从基础闭环验证变成业务编排演示。
- 最小闭环足以证明现有散点能力已经能连线。

### Decision 2: 通过真实 SchedulingService 路径触发插件

CLI 不直接 import 插件类，也不直接调插件 helper，而是：

- 通过 Registry 找到 `quantagent.official.source.placeholder`
- 构造 `PluginSchedulingService`
- 调用 `trigger()`

原因：

- 演示目标是“系统链路连通”，不是“插件本身能跑”。
- 只有经过 SchedulingService，才能同时覆盖 runtime invoke 和 event bridge。

### Decision 3: 使用 InMemoryEventBus + 单一 fake consumer

本轮固定使用 `InMemoryEventBus`，并注册一个本地 fake consumer 订阅 `source.event.captured`。

fake consumer 行为仅限于：

- 记录是否收到事件
- 打印 topic / event id / payload summary

原因：

- 这样能最小化依赖，避免 Kafka/DB 成为 demo 阻塞项。
- fake consumer 只负责“证明收到”，不承担任何后续业务节点职责。

### Decision 4: 输出采用人类可读日志

CLI 输出固定为类似：

```text
🔍 Scanning plugins... found N plugin(s)
✅ quantagent.official.source.placeholder v0.1.0

🚀 Triggering plugin: source.fetch
Plugin: quantagent.official.source.placeholder
Status: SUCCEEDED

📤 Event published to: source.event.captured
Event ID: evt_xxx

📩 Consumer received event!
Topic: source.event.captured

✨ Demo complete! The full pipeline works.
```

原因：

- 本轮主要面向维护者/开发者肉眼确认链路效果。
- 不需要为了 demo 先定义结构化输出协议。

### Decision 5: 失败路径明确但不扩 scope

CLI 失败时只需要：

- 返回非零退出码
- 打印最小错误摘要

不要求：

- 重试
- fallback
- metrics
- outbox
- 复杂日志框架集成

原因：

- 这只是验证入口，不是生产 runtime 组件。

## Data Flow

```text
RegistryScanner / PluginRegistry
  -> find quantagent.official.source.placeholder
  -> PluginSchedulingService.trigger(source.fetch)
  -> PluginRuntimeService.invoke()
  -> SourceEventPublisher.publish_source_fetch_result()
  -> InMemoryEventBus.publish(source.event.captured)
  -> fake consumer receives envelope
  -> CLI prints success
```

## File / Module Plan

实现阶段预期新增：

```text
packages/core/src/quantagent/core/demo.py
```

该文件只负责：

- 初始化 InMemoryEventBus
- 注册 fake consumer
- 构建 Registry / Runtime / SchedulingService
- 触发 placeholder plugin
- 打印结果和退出码

实现阶段预期修改：

```text
packages/core/pyproject.toml
```

仅新增 CLI entrypoint：

```text
quantagent-demo
```

## Risks / Trade-offs

- 如果桥接层未来支持更多 capability，本 demo 仍然只验证 `source.fetch`，不会自动覆盖新能力。
- 使用 `placeholder-source` 能降低依赖，但不能证明 RSS/real reader/provider 场景已就绪；这符合本轮目标。
- 人类可读日志更直观，但不适合作为稳定自动化协议；本轮接受这个取舍。

## Migration Plan

1. 提交本 OpenSpec-only PR。
2. 获批后，在实现 PR 中新增 `demo.py` 和 `quantagent-demo` 入口。
3. 复用现有 bridge 和 in-memory bus，不新增新架构层。
4. 后续若需要 Kafka / worker / scheduler 实际运行演示，再开独立 change。

## Open Questions

- 无。本 change 范围固定，无新增待确认设计决策。
