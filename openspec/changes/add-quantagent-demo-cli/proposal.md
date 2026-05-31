## 背景 / 为什么现在做

Issue #205 的目标不是继续扩展业务链路，而是把当前已经分散存在的几个核心能力收成一个一键演示入口：

- Registry 扫描官方插件
- `PluginSchedulingService.trigger()` 触发 `source.fetch`
- `scheduling-event-bus-bridge-v1` 已建立的 `source.fetch -> source.event.captured` 发布桥接
- InMemoryEventBus 上的最小 fake consumer

当前这些能力分别已经存在，但还没有一个人类可读、无需 Kafka/DB/外部服务的 CLI 演示来证明“插件发出的消息已经能进入总线，并且有下游 consumer 收到”。

## 当前要收住的问题

QuantAgent 需要一个最小 CLI demo，稳定证明 `plugin scan -> source.fetch trigger -> source.event.captured publish -> fake consumer receive` 这条链路已连通。

## 目标

- 新增 `quantagent-demo` CLI 入口，演示当前最小闭环。
- 只使用 `InMemoryEventBus` 和官方 `placeholder-source`，不依赖 Kafka、DB 或外部网络。
- 输出采用人类可读日志，明确展示扫描、触发、发布、消费四个步骤。
- CLI 通过真实 `PluginSchedulingService` 调度路径驱动插件，而不是直接调用插件 helper。
- fake consumer 只证明“收到事件”，不继续做 analysis / strategy / approval / broker 等业务扩展。

## 明确不做

- 不演示 `RSS -> analysis -> strategy -> discord -> approval -> broker` 全业务链。
- 不引入 Kafka、PostgreSQL、Scheduler loop、Worker app 或 Web 前端。
- 不增加新的插件类型、事件主题或运行时桥接协议。
- 不把 demo 演变成通用 orchestration framework。
- 不在本 change 中实现 Discord、Tavily、Approval 或 Broker 集成。

## 相关上下文

- Issue #205
- `openspec/changes/scheduling-event-bus-bridge-v1/`
- `packages/core/src/quantagent/core/scheduling/service.py`
- `packages/core/src/quantagent/core/events/`
- `plugins/sources/placeholder-source/`

## 前置依赖

- `scheduling-event-bus-bridge-v1` 已存在，demo 复用其桥接能力。
- 无其他已知阻塞。

## 待确认问题

- 无。本 change 只收最小 CLI demo，不引入新的架构分歧。

## 子任务树

- [ ] 新增 `add-quantagent-demo-cli` OpenSpec artifacts，并通过严格校验。
- [ ] 明确 CLI 输出格式、fake consumer 行为、依赖边界和失败信号。
- [ ] 提交 OpenSpec-only PR，等待维护者确认后再进入实现 PR。

## 验收口径

必须成立：

- OpenSpec 能明确描述 `quantagent-demo` 的输入依赖、执行链路和输出行为。
- CLI 演示必须通过 Registry + Scheduling + EventBus 的真实组合路径运行。
- fake consumer 必须实际收到 `source.event.captured`，而不是只打印假日志。
- 演示不依赖 Kafka/DB/外部服务。

明确不成立：

- 直接硬编码插件对象绕过 Registry。
- 直接调用插件 helper 绕过 `PluginSchedulingService`。
- 在本 change 中把 demo 扩成业务主链演示。

失败信号：

- consumer 没收到事件。
- 需要 Kafka/DB 才能跑通。
- 为了 demo 再新增一套与现有桥接平行的发布逻辑。

## Harness / 验证要求

本 OpenSpec 阶段至少运行：

```bash
openspec validate add-quantagent-demo-cli --type change --strict --json
```

实现阶段预期最小验证：

```bash
uv run quantagent-demo
```

并确认控制台输出包含扫描、触发、发布和消费四个阶段。

## 架构 / 分层风险

- 本 change 只在 `packages/core` 范围内引入 CLI 演示入口，不能把 demo 逻辑塞进 API/router 或插件实现。
- fake consumer 是演示层，不应反向定义新的 Event Bus 契约。
- 复用现有 `scheduling-event-bus-bridge-v1` 能力，避免再造第二套桥接路径。
- 不新增 package，不改变现有依赖方向。

## OpenSpec 处理

- 新建独立 change：`add-quantagent-demo-cli`
- 原因：`#205` 的 CLI demo 是对 bridge 能力的演示与整合，不应继续扩大 `scheduling-event-bus-bridge-v1` 的 change 范围
- 本次仅准备 OpenSpec-only PR，不进入实现代码
