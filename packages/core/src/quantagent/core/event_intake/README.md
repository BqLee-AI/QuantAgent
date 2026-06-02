# event_intake

`quantagent.core.event_intake` 是 V1 AI event intake / routing 的受控边界。它消费 `industry.analysis.requested` 的 bounded snapshot，最多执行一次结构化模型调用，产出 `EventIntakeDecisionV1`，再通过 `event.routed` 发布 `discard`、`route` 或 `review` outcome。

## 职责

- 定义 `IndustryEventContextV1`，覆盖 trace、source、article、industry candidates、routing policy 和 input budget。
- 定义 `EventIntakeDecisionV1`，覆盖质量过滤、行业相关性、结构化新闻、路由、审计和 schema consistency rules。
- 提供 `SingleCallEventIntakeRunner` 和 `StructuredModelInvoker` provider port。
- 提供 fake provider harness，用 fixture 验证每个 article item 最多一次 provider invocation。
- 提供 `EventIntakeRoutedPublisher`，把 outcome 发布到稳定 topic `event.routed`。

## 非职责

- 不执行深度行业分析。
- 不做 scoring / debate、Decision、Approval、Notification 或 broker。
- 不做 tool-call loop、multi-turn agent loop、二次网页抓取或模型分块总结。
- 不保存完整 prompt、完整 provider raw response、完整 chain-of-thought、secret、ORM object、plugin instance 或 provider client。

## Provider 边界

V1 先在 core 内定义可迁移的 provider port，是因为 `packages/agent` 当前仍是预留 package，尚未纳入 Python workspace。worker 只能注入 `StructuredModelInvoker`，不能直接创建 provider SDK client。后续 AgentRuntime 落地后，可以用 AgentRuntime adapter 替换该 port，而不改变 worker consumer 或 `event.routed` contract。

默认 `ReviewOnlyStructuredModelInvoker` 不调用真实模型，只输出 `decision=review` 并标记 `PROVIDER_NOT_CONFIGURED`。测试和本地验收应优先使用 `FakeStructuredModelInvoker`。
