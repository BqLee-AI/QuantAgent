## 1. 数据结构与 composition root

- [ ] 1.1 在 `apps/scheduler/src/quantagent/scheduler/main.py` 新增 `SchedulerRuntime` dataclass（字段：`event_bus: EventBusRuntime`、`scheduling: PluginSchedulingService`、`registry: PluginRegistry`，方法：`async def close()`)
- [ ] 1.2 重写 `create_scheduler_runtime()`：调用 `build_event_bus_runtime()` + `build_plugin_registry()` + `PluginRuntimeService()` + `InMemoryPluginRunRepository()`，注入 `publisher=runtime.publisher` 构建 `PluginSchedulingService`，返回 `SchedulerRuntime`

## 2. run() 入口实现

- [ ] 2.1 重写 `run()` 为 `asyncio.run(_run())`，`_run()` 中调用 `create_scheduler_runtime()`
- [ ] 2.2 在 `_run()` 中读取 `SCHEDULE_PLUGIN_ID` 环境变量（默认 `quantagent.official.source.placeholder`），构造 `PluginTriggerRequest`（capability=`source.fetch`，trigger_type=`MANUAL`）
- [ ] 2.3 调用 `scheduling.trigger(request)`，获取 `PluginRunRecord`
- [ ] 2.4 用 `logging` 输出结构化字段（run_id、status、duration_ms、plugin_id、capability），成功为 INFO，失败为 WARNING
- [ ] 2.5 在 try/finally 中调用 `runtime.close()` 优雅退出，成功退出码 0，失败退出码 1

## 3. 配置调整

- [ ] 3.1 确认 `Settings.EVENT_BUS_BACKEND` 默认值为 `"kafka"`（当前为 `"memory"`，需要改为 `"kafka"` 使 scheduler 默认走 Kafka；注意只改 scheduler app 的 settings 子集，不影响 core 全局默认）
- [ ] 3.2 在 `apps/scheduler` 的环境配置中新增 `SCHEDULE_PLUGIN_ID` 默认值说明

## 4. Memory 后端单元测试

- [ ] 4.1 更新 `test_scheduler_runtime_uses_memory_backend_by_default`：验证 `SchedulerRuntime`（而非原 `EventBusRuntime`）的 `event_bus.backend` 和 `event_bus.publisher`
- [ ] 4.2 新增测试：memory 后端下 `create_scheduler_runtime()` 组装的 `scheduling` 实例正确持有 publisher
- [ ] 4.3 新增测试：memory 后端下触发成功后，通过 `InMemoryEventBus.subscribe()` 捕获到 `source.event.captured` 事件

## 5. Kafka 后端单元测试

- [ ] 5.1 新增测试：mock `EVENT_BUS_BACKEND=kafka` + `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092`，验证 `SchedulerRuntime.event_bus.publisher` 为 `KafkaEventBusPublisher` 实例
- [ ] 5.2 新增测试：Kafka 后端下 mock `KafkaEventBusPublisher.publish`，触发插件后验证 `publish` 被调用且 `EventEnvelope.topic == "source.event.captured"`
- [ ] 5.3 新增测试：`EVENT_BUS_BACKEND=kafka` 且 `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS` 为空时，`create_scheduler_runtime()` 抛出 `EventBusError`

## 6. 边界与错误路径测试

- [ ] 6.1 新增测试：`SCHEDULE_PLUGIN_ID` 指定的插件未注册时，trigger 返回 FAILED 状态
- [ ] 6.2 新增测试：`run()` 在触发失败时仍调用 `runtime.close()`
- [ ] 6.3 新增测试：结构化日志输出包含正确字段（用 `caplog` 或 mock logger 验证）
