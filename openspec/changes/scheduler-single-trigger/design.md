## Context

`apps/scheduler` 当前是一个空壳：`create_scheduler_runtime()` 只创建 `EventBusRuntime`，`run()` 创建后直接退出。前置 issue #204 已完成核心桥接——`PluginSchedulingService` 接受可选 `EventBusPublisher`，`trigger()` 成功路径自动发布 `source.event.captured` 事件。现在需要 scheduler app 把所有零件组装起来，完成 **插件调度 → 事件总线 → 消费** 链路的第一个端到端闭环。

### 现有组件

| 组件 | 位置 | 职责 |
|---|---|---|
| `EventBusRuntime` | `core/events/service.py` | 根据 settings 创建 Kafka 或 InMemory publisher/consumer |
| `PluginRegistry` | `core/registry/service.py` | 扫描插件目录，提供 `get_plugin()` |
| `PluginRuntimeService` | `core/runtime/service.py` | 加载插件 entrypoint，执行 invoke 生命周期 |
| `PluginSchedulingService` | `core/scheduling/service.py` | 编排 trigger 流程，含 precheck/invoke/audit/event-publish |
| `InMemoryPluginRunRepository` | `core/scheduling/repository.py` | 内存审计记录存储 |
| `build_event_bus_runtime()` | `core/events/service.py` | 工厂：按 settings 组装 EventBusRuntime |
| `build_plugin_registry()` | `core/registry/service.py` | 工厂：按默认目录组装 PluginRegistry |

### 调用链路（目标）

```
run()
  ├── create_scheduler_runtime()
  │     ├── build_event_bus_runtime(settings)      → EventBusRuntime
  │     ├── build_plugin_registry()                → PluginRegistry
  │     ├── PluginRuntimeService()                 → runtime service
  │     ├── InMemoryPluginRunRepository()          → repository
  │     └── PluginSchedulingService(               → scheduling service
  │           registry, runtime, repository,
  │           publisher=runtime.publisher)
  │     → SchedulerRuntime(event_bus, scheduling)
  │
  ├── scheduling.trigger(request)
  │     ├── registry.get_plugin(plugin_id)
  │     ├── runtime.invoke(record, capability="source.fetch")
  │     └── source_publisher.publish(result)       → Kafka / memory
  │
  └── runtime.close()                              → 优雅退出
```

## Goals / Non-Goals

**Goals:**

1. `create_scheduler_runtime()` 组装完整的 `SchedulerRuntime`（封装 EventBusRuntime + PluginSchedulingService + PluginRegistry）
2. `run()` 触发一次 `source.fetch`，通过事件总线发布结果，然后优雅退出
3. 通过 `SCHEDULE_PLUGIN_ID` 环境变量控制触发哪个插件（默认 `quantagent.official.source.placeholder`）
4. `run()` 输出结构化 JSON 日志（run_id、status、duration_ms、plugin_id）
5. 测试中可用 `EVENT_BUS_BACKEND=memory` 验证组装正确性

**Non-Goals:**

- 不实现定时循环调度（interval loop），那是后续 issue
- 不引入新的服务发现或配置中心
- 不修改 `PluginSchedulingService`、`SourceEventPublisher` 或 core 的任何接口
- 不处理非 `source.fetch` capability 的调度
- 不实现插件执行结果的重试或失败补偿

## Decisions

### D1: 事件总线后端策略——Kafka 为默认，memory 仅用于测试

**决策**: scheduler app 的 `EVENT_BUS_BACKEND` 默认为 `kafka`。`memory` 后端**仅用于单元测试**，不作为运行时配置选项暴露给用户。

**理由**:
- `InMemoryEventBus` 不支持跨进程通信，scheduler 和 worker 必须通过 Kafka 解耦
- Docker Compose 已包含 Kafka 服务，生产环境天然可用
- memory 后端的存在价值是让单元测试能在无 Kafka 的 CI 环境中验证组装正确性

**测试策略**:
- **Kafka 路径单元测试**: mock `KafkaEventBusPublisher.publish`，验证在 `EVENT_BUS_BACKEND=kafka` 下 `create_scheduler_runtime()` 正确组装 `KafkaEventBusPublisher`/`KafkaEventBusConsumer`，且触发成功后 `publish` 被调用并传入正确的 `EventEnvelope`（topic=`source.event.captured`，payload 含 plugin_id 和 items）。不依赖真实 Kafka 实例。
- **Memory 路径单元测试**: 使用 `EVENT_BUS_BACKEND=memory` + `InMemoryEventBus`，验证组装正确性并通过 `subscribe()` + handler 捕获验证事件端到端传递。
- **配置缺失测试**: 验证 `EVENT_BUS_BACKEND=kafka` + 缺少 `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS` 时抛出 `EventBusError`。

**替代方案**: 保留 memory 作为运行时降级方案 → 放弃，因为 scheduler 和 worker 分属不同进程，memory 后端无法传递事件，降级无意义。

### D2: 新建 SchedulerRuntime dataclass 作为 composition root

**决策**: 新增 `SchedulerRuntime` dataclass，封装 `EventBusRuntime`、`PluginSchedulingService` 和 `PluginRegistry`。

```python
@dataclass
class SchedulerRuntime:
    event_bus: EventBusRuntime
    scheduling: PluginSchedulingService
    registry: PluginRegistry

    async def close(self) -> None:
        await self.event_bus.close()
```

**理由**:
- 语义清晰，测试可直接检查 `scheduling` 实例而非解析 tuple
- `close()` 委托给 EventBusRuntime，未来可扩展清理逻辑
- 不引入额外抽象层，只是 composition root 的结构化表达

**替代方案**: 返回 `(EventBusRuntime, PluginSchedulingService)` tuple → 可读性差，测试断言不够自解释。

### D3: 环境变量 SCHEDULE_PLUGIN_ID 使用完整插件 ID

**决策**: `SCHEDULE_PLUGIN_ID` 直接使用 registry 中的完整插件 ID（如 `quantagent.official.source.placeholder`），不做名称映射。

**理由**:
- 与 `registry.get_plugin()` 直接对齐，零映射逻辑
- 避免引入维护一个名称→ID 映射表的额外负担
- 环境变量值可从 `plugin.yaml` 的 `id` 字段直接复制

**默认值**: `quantagent.official.source.placeholder`（placeholder-source 插件）。

### D4: run() 结构化日志输出

**决策**: `run()` 在触发完成后通过 `logging` 输出结构化字段（`run_id`、`status`、`duration_ms`、`plugin_id`、`capability`），级别为 INFO。

**理由**:
- 方便 worker 端用 `run_id` 对齐排查
- 结构化字段可被日志收集器（Loki/ELK）直接索引
- 不依赖 print，与项目现有 logging 体系一致

### D5: run() 使用 asyncio.run() 入口

**决策**: `run()` 用 `asyncio.run()` 包装异步调度逻辑，保持 CLI 入口同步。

**理由**:
- 与 `quantagent-scheduler` CLI 点号入口（typer/click）兼容
- scheduler 不是长期运行服务（当前），一次性触发后退出
- 未来改为 interval loop 时，入口结构不变，只改内部循环

### D6: 插件目录路径硬编码为默认值

**决策**: 调用 `build_plugin_registry()` 时使用默认路径（`plugins/` + `runtime/plugins/`），不新增环境变量覆盖。

**理由**:
- 与 API app 行为一致，减少配置面
- 如果需要自定义路径，是独立的配置增强 issue，不属于本次范围

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| placeholder-source 插件未安装导致 get_plugin() 返回 None | `PluginSchedulingService.trigger()` 已有 `PLUGIN_NOT_FOUND` 错误处理，日志会打印具体 plugin_id |
| Kafka 不可用时启动失败 | `EventBusSettings.validate()` 在启动时校验 bootstrap servers，快速失败并给出明确错误信息 |
| 单次触发无重试机制 | Non-goal；重试和补偿在后续 interval loop issue 中设计 |
| `asyncio.run()` 不支持嵌套调用 | `run()` 是顶层入口，不会在已有 event loop 内被调用；测试直接调用内部异步函数绕过 |

## Open Questions

- 是否需要 `SCHEDULE_CAPABILITY` 环境变量支持触发非 `source.fetch` 的 capability？当前 hardcode 为 `source.fetch`，后续 interval loop issue 可扩展。
