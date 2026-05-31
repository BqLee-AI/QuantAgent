## 1. OpenSpec 评审

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `openspec/changes/scheduling-event-bus-bridge-v1/**`，不混入实现、依赖升级或格式化。
- [ ] 1.2 在 PR 说明中链接 issue #204，写清楚桥接目标和零回归保证。
- [ ] 1.3 等维护者在 PR 下明确评论"没问题"或批准后，再进入实现 PR。

## 2. 桥接代码

- [ ] 2.1 `PluginSchedulingService.__init__` 新增 `publisher: EventBusPublisher | None = None` 参数。
- [ ] 2.2 新增 `_publish_source_result` 方法：从 `invocation.result.output` 重建 `SourceFetchResult`，通过 `SourceEventPublisher` 发布 `source.event.captured`。
- [ ] 2.3 在 `trigger()` 的 SUCCEEDED 返回路径中，检查 publisher 和 capability，调用 `_publish_source_result`。
- [ ] 2.4 发布失败 catch + warning 日志，不改变 `PluginRunRecord` 状态。
- [ ] 2.5 `publisher=None` 时所有行为与现有一致。

## 3. 单元测试

- [ ] 3.1 新增 `test_trigger_publishes_source_event_when_publisher_provided`：使用 `InMemoryEventBus` + `RecordingHandler` 验证事件发布。
- [ ] 3.2 新增 `test_trigger_without_publisher_behaves_identically`：确认无 publisher 时行为不变。
- [ ] 3.3 新增 `test_trigger_does_not_publish_for_non_source_capability`：验证 capability 过滤。
- [ ] 3.4 新增 `test_trigger_publish_failure_does_not_affect_run_record`：验证发布失败不影响调度记录。
- [ ] 3.5 确认现有 `test_scheduling.py` 全部通过，不修改任何已有测试。

## 4. 后续拆分

- [ ] 4.1 实现 PR 合入后，依次推进 #205（CLI demo）、#206（scheduler app）、#207（worker app）。
- [ ] 4.2 后续 issue 引入失败路径 `runtime.failed` 事件发布。
- [ ] 4.3 后续 issue 引入非 source.fetch capability 的发布支持。
