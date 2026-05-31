## 1. OpenSpec 评审

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `openspec/changes/add-quantagent-demo-cli/**`，不混入实现、依赖升级或格式化。
- [ ] 1.2 在 PR 说明中链接 issue #205 和 `scheduling-event-bus-bridge-v1`，写清楚 demo 只验证最小 source 事件闭环。
- [ ] 1.3 等维护者明确评论“没问题”或批准后，再进入实现 PR。

## 2. CLI Demo 设计

- [ ] 2.1 固定 demo 使用 `InMemoryEventBus`，不依赖 Kafka / DB / 外部服务。
- [ ] 2.2 固定 demo 插件为 `quantagent.official.source.placeholder`。
- [ ] 2.3 固定执行路径为 Registry -> SchedulingService.trigger() -> event publish -> fake consumer receive。
- [ ] 2.4 固定 fake consumer 只负责接收并打印事件，不扩展 analysis / strategy / approval / broker。
- [ ] 2.5 固定输出为人类可读日志，并定义成功/失败退出码。

## 3. 实现后最小验证

- [ ] 3.1 `uv run quantagent-demo` 能扫描到 placeholder plugin。
- [ ] 3.2 `uv run quantagent-demo` 能成功触发 `source.fetch`。
- [ ] 3.3 CLI 输出能明确显示 `source.event.captured` 已发布。
- [ ] 3.4 fake consumer 确实收到事件并打印 payload summary。
- [ ] 3.5 无 Kafka / DB / 外部服务时仍可独立运行。
