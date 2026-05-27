## 背景

Plugin Runtime V1 已经收住了插件加载、配置注入、生命周期和统一 `invoke` transport，但插件能力输入输出仍停留在“通用 mapping 可以通过”的层级。当前 `PluginInvokeRequest` / `PluginInvokeResult` 适合作为 runtime transport，却还不能回答另一层更关键的问题：不同插件能力到底应该接收什么、返回什么，哪些字段可被 API、worker、审计和后续核心链路稳定消费。

如果这条边界不先收住，RSS、crawler、Discord、notification 等插件会各自返回私有结构。那样即使 Runtime 已经统一，后续 `RawEvent` 转换、通知日志、审计记录、控制台展示和 contract test 仍然会因为 DTO 不统一而反复分叉。

本 change 聚焦 Plugin IO DTO V1：在 Runtime V1 的通用 `invoke` 壳子之上，定义第一版 typed input/output DTO，先覆盖 `source.fetch` 与 `notification.send` 两类 capability，并明确插件返回的是 draft / result，而不是数据库模型或 core 内部对象。

## 改动

- 定义 Plugin IO DTO V1 的分层：保留 Runtime V1 通用 `PluginInvokeRequest` / `PluginInvokeResult` 作为 transport，并把 `PluginInput` / `PluginResult` 定义为 capability-specific typed payload 的抽象边界。
- 定义 DTO 实现默认形态：沿用当前 `packages/plugin-sdk` 的冻结 `dataclass` 风格，但 contract 以 JSON-like、可校验、可序列化和只读语义为准。
- 定义 `source.fetch` 第一版 typed DTO，包括 `SourceFetchInput`、`SourceFetchResult` 和中性的 `SourceItemDraft`。
- 定义 `notification.send` 第一版 typed DTO，包括 `NotificationSendInput`、`NotificationSendResult` 和最小文本消息发送边界。
- 定义 typed DTO 与 core 内部对象的边界：插件返回 draft / result，core 再决定是否转换为 `RawEvent`、`NotificationLog`、`AuditLog` 或其他内部对象。
- 定义 DTO 的校验、序列化、可审计和脱敏要求，并保持结构化错误继续沿用 Runtime V1 已有 `PluginError` 形状。

## 能力

### 新增能力

- `plugin-io-dto-v1`: 定义 QuantAgent 插件 IO DTO V1 的 typed input/output contract，先覆盖 `source.fetch` 和 `notification.send`。

## 影响

- `packages/plugin-sdk/**`：后续实现 typed DTO dataclass、必要的校验 / 序列化 helper 和 capability-specific contract test。
- `packages/core/src/quantagent/core/runtime/**`：后续继续复用现有通用 invoke transport，不在本 change 中重写 Runtime V1 生命周期或 transport 协议。
- `plugins/**` 与 `runtime/plugins/**`：后续 source / notification 插件应基于本 change 的 typed DTO 输出草案对象，而不是各自返回私有 Python 结构。
