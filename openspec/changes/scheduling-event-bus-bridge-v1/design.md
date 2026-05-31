## Context

`PluginSchedulingService.trigger()` 已经具备完整的插件调度能力：验证插件 → 调用 runtime → 记录审计 → 返回 `PluginRunRecord`。但调度完成后没有任何事件通知机制，下游服务无法感知插件执行结果。

`SourceEventPublisher`（`events/service.py`）已经知道如何把 `SourceFetchResult` 转为 `source.event.captured` 事件的 `EventEnvelope` 并通过 `EventBusPublisher` 发布。`InMemoryEventBus` 和 `KafkaEventBusPublisher` 都已实现 `EventBusPublisher` Protocol。

本 change 只需要在两者之间建立桥接。

## Goals / Non-Goals

**Goals:**

- 让 `PluginSchedulingService` 在成功执行 `source.fetch` 后，将结果通过 `EventBusPublisher` 发布。
- 保持调度服务和事件总线的关注点分离：发布失败不影响调度记录。
- 保持零回归：无 publisher 时行为不变。
- 为后续 CLI demo、scheduler app、worker app 的端到端验证奠定基础。

**Non-Goals:**

- 不引入通用事件发布协议（不按 capability 注册 publisher）。
- 不处理非 `source.fetch` capability 的事件发布（后续按需扩展）。
- 不修改 `SourceEventPublisher`、`EventBusPublisher`、`EventEnvelope` 等已有接口。
- 不引入 Kafka 或任何外部基础设施依赖（桥接层只依赖 Protocol）。
- 不实现失败路径的 `runtime.failed` 事件发布（后续 issue）。
- 不实现定时调度循环（后续 issue）。

## Decisions

### 1. 通过构造函数注入可选 EventBusPublisher

`PluginSchedulingService.__init__` 新增参数：

```python
def __init__(
    self,
    *,
    registry: PluginRegistry,
    runtime: PluginRuntimeService,
    repository: PluginRunRepository,
    clock: SchedulingClock | None = None,
    publisher: EventBusPublisher | None = None,  # 新增
) -> None:
```

选择构造函数注入而非运行时参数，原因：
- 与已有的 registry/runtime/repository 注入风格一致。
- publisher 是服务级依赖，不是每次调用变化的参数。
- 可选参数保持零回归。

### 2. 仅 source.fetch 成功路径发布

发布条件：

```text
publisher is not None
AND run.status == SUCCEEDED
AND request.capability == "source.fetch"
AND invocation.result is not None
AND invocation.result.output is not None
```

仅处理 `source.fetch` 的原因：
- 这是当前唯一有 `SourceEventPublisher` 支持的 capability。
- 其他 capability 的发布需要各自的事件格式，后续按需引入。
- 避免一次性过度设计通用发布机制。

### 3. 发布逻辑委托给 SourceEventPublisher

不在 `PluginSchedulingService` 中直接构造 `EventEnvelope`，而是复用已有的 `SourceEventPublisher.publish_source_fetch_result()`。这样：

- 调度服务只需要知道"发布"这个动作，不需要知道 envelope 结构。
- envelope 构造逻辑集中在 `events/service.py`，保持单一职责。
- 后续如果 envelope 格式变化，只改 `SourceEventPublisher`。

转换链路：

```text
invocation.result.output (dict)
  → SourceFetchResult.from_mapping(output, stage="publish")
  → SourceEventPublisher.publish_source_fetch_result(result, ...)
  → EventEnvelope → EventBusPublisher.publish(envelope)
```

`from_mapping` 的 `stage` 参数传入 `"publish"` 而非默认 `"invoke"`，保持审计归属清晰：DTO 校验失败时的错误信息会标记为 publish 阶段，不会误导排查者以为问题出在插件调用。

参数映射（`publish_source_fetch_result` 的关键字参数）：

```text
producer       = "plugin-scheduling"
request_id     = validated_request.request_id
plugin_id      = validated_request.plugin_id
causation_id   = run.run_id
```

### 4. 发布失败不改变调度记录

发布失败的处理策略：

```python
try:
    await self._publish_source_result(invocation, run, validated_request)
except Exception:
    logger.warning(
        "Event publish failed after successful scheduling.",
        extra={"plugin_id": run.plugin_id, "run_id": run.run_id, "error_type": exc.__class__.__name__},
    )
```

warning 日志必须包含 `plugin_id`、`run_id`、`error_type`，确保生产环境可排查。

原因：
- 调度层和发布层是不同关注点。调度已成功，不应因为发布失败而标记调度为 FAILED。
- 后续如果需要严格保证"发布成功才算成功"，可以引入 outbox pattern（独立 issue）。
- V1 先保证调度链路不被发布故障拖垮。

### 5. capability 过滤由调度服务内部处理

不在 `EventBusPublisher` 层做 capability 过滤，而是在调度服务内部判断。原因：
- EventBusPublisher 是通用传输协议，不应理解业务语义。
- 调度服务是唯一知道当前 capability 的地方。
- 过滤逻辑简单（一个 if 判断），不需要额外抽象。

## Risks / Trade-offs

- [风险] 仅处理 source.fetch 会导致其他 capability 的发布需要重复类似逻辑。
  缓解：V1 先验证桥接模式可行，后续如需支持多 capability，可以提取通用发布策略。

- [风险] 发布失败被静默吞掉，可能导致下游长时间收不到事件而不自知。
  缓解：V1 先 warning 级日志，后续可引入 metrics / health check / outbox。

- [风险] `SourceFetchResult.from_mapping()` 在 output 不是合法 SourceFetchResult 时会抛异常。
  缓解：try/except 已覆盖，异常不会影响调度记录。

## Migration Plan

1. 提交本 OpenSpec-only PR。
2. 维护者审批后，进入实现 PR。
3. 实现 PR 改动 `packages/core/src/quantagent/core/scheduling/service.py`，新增可选 publisher 和发布逻辑。
4. 实现 PR 在 `packages/core/tests/test_scheduling.py` 新增单元测试。
5. 后续 PR 依次实现 CLI demo、scheduler app、worker app。

## Open Questions

- 无。本 change 范围明确，无待确认的设计决策。
