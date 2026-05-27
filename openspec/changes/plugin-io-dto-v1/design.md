## 背景

Issue #142 要解决的不是“Runtime 能不能调用插件”，而是“插件被调用后，平台如何稳定理解它的输入输出”。Runtime V1 已经定义了统一 `invoke` transport：

- `PluginInvokeRequest(capability, request_id, input, metadata)`
- `PluginInvokeResult(output, metadata)`
- 结构化 `PluginRuntimeError` / `PluginError`

这层通用 transport 很适合表达宿主如何发起调用，但它故意保持中性，并没有为 `source.fetch` 或 `notification.send` 提供 typed contract。如果现在让每个插件自行决定 `output` 里放什么字段，后续转换、审计和测试会继续分叉。

## 目标与非目标

**目标：**

- 在不替换 Runtime V1 transport 的前提下，定义第一版 typed IO DTO。
- 明确 `PluginInput` / `PluginResult` 是 capability-specific typed payload 的抽象边界，Runtime transport 只是承载层。
- 沿用当前 `packages/plugin-sdk` 冻结 `dataclass` 的实现默认风格，但 contract 以 JSON-like、可校验、可序列化和只读语义为准。
- 定义 `source.fetch` 的第一版 input/output，确保 source 插件输出的是中性草案对象，而不是持久化对象。
- 定义 `notification.send` 的第一版 input/output，确保 notification 插件能以统一方式表达发送请求与发送结果。
- 定义 typed DTO 与 core 内部对象的转换边界：插件返回 draft / result，由 core 决定如何落库或继续进入后续链路。
- 定义 typed DTO 的最小 validation / serialization contract test 方向。

**非目标：**

- 不替换现有 `PluginInvokeRequest` / `PluginInvokeResult` transport。
- 不在本轮扩展到 industry、strategy、broker 或所有未来 capability。
- 不在本轮定义完整 serializer framework、schema-driven form、Event Bus payload 或 ORM model。
- 不在本轮实现 RawEvent 入库、Notification 持久化、Scheduler 或 API 层消费逻辑。
- 不引入 Pydantic-only 或 TypedDict-only 作为新的唯一 DTO 真源。

## 决策

### 1. Typed DTO 叠在 Runtime V1 通用 transport 上

Plugin IO DTO V1 SHALL 保留 Runtime V1 现有的通用 `PluginInvokeRequest` / `PluginInvokeResult` 作为宿主 transport。Typed DTO 在语义层表达 capability-specific input/output，而不是替换 transport 自身。

这意味着后续实现中：

- Runtime 仍然运输 JSON-like / mapping 数据。
- Typed DTO 负责定义 `input` / `output` 的字段语义。
- 插件作者和 core contract test 可以围绕 typed DTO 编码。
- 宿主与 typed DTO 的互转由 helper / adapter 负责，而不是在 runtime 中写 `if capability == ...` 的业务分支。

替代方案是直接让 runtime transport 改为能力专用 DTO。该方案会反向影响已落地的 Runtime V1 边界，使 `invoke` 从通用壳子退化为 capability-aware runtime，因此不采用。

### 2. `PluginInput` / `PluginResult` 是 typed payload 抽象边界

Issue #142 中的 `PluginInput` / `PluginResult` 不应另起一套 runtime transport。Plugin IO DTO V1 SHALL 将它们定义为 capability-specific typed payload 的抽象边界：

- `PluginInput` 表达某个 capability 的 typed input payload。
- `PluginResult` 表达某个 capability 的 typed output payload。
- Runtime V1 继续通过 `PluginInvokeRequest.input` 和 `PluginInvokeResult.output` 承载 JSON-like payload。
- 每个 capability 的 typed DTO 负责定义 payload 字段、校验和序列化语义。

这样可以闭合 issue 中的通用 IO 边界，又不会把 Runtime V1 改造成 capability-aware runtime。

### 3. DTO 实现默认沿用冻结 dataclass，但 spec 约束行为

`packages/plugin-sdk` 当前已经使用冻结 `dataclass` 和只读 mapping 表达 Runtime DTO。Plugin IO DTO V1 SHOULD 保持同样风格，以减少两套对象模型并存的心智负担。

但是 OpenSpec contract 不应只依赖 Python 具体实现形态。V1 的强约束是：

- DTO 字段语义稳定。
- DTO 可以校验必填字段、字段类型和 JSON-safe 值。
- DTO 可以序列化为 JSON-like mapping。
- DTO 对调用方表现为只读语义。

这样做的好处：

- 与 RuntimeContext、PluginInvokeRequest、PluginInvokeResult 的风格一致。
- 足以表达第一版 typed 字段和只读契约。
- 不要求本轮在 SDK 中引入新的运行时校验框架。

这不排斥后续通过 helper 或 schema 补充序列化/校验，但 V1 的“真源风格”先保持 dataclass 一致性。

### 4. Source 第一版输出命名为 `SourceItemDraft`

`source.fetch` 的输出对象 SHALL 使用中性的 `SourceItemDraft` 命名，而不是直接命名为 `RawEventDraft` 或 `EventDraft`。

原因：

- Source Plugin 的职责是抓取、解析和标准化原始信息，不直接决定 core 如何持久化。
- `RawEvent` 属于 core 事件链路对象；过早在插件 DTO 层绑定 `RawEvent` 会让 source 输出和持久化边界混淆。
- `SourceItemDraft` 更准确表达“插件返回一条 source 产物草案，由平台后续处理”。

### 5. `source.fetch` 只收最小 typed contract

`source.fetch` 第一版 SHOULD 定义：

- `SourceFetchInput`
- `SourceFetchResult`
- `SourceItemDraft`

其中：

- input 表达一次 source fetch 所需的 capability-specific 入参和 metadata。
- result 表达一次 fetch 的整体结果、items 列表和必要元数据。
- item draft 表达单条 source 产物的公共字段。

V1 不要求一次性收住所有 source 类型的专属字段，只要求稳定最小公共字段和 metadata 承载面。

建议的最小字段如下：

```text
SourceFetchInput
  query: string | null
  limit: integer | null
  cursor: string | null
  metadata: object

SourceItemDraft
  external_id: string | null
  url: string | null
  title: string | null
  content: string | null
  author: string | null
  published_at: string | null
  captured_at: string | null
  raw_payload: object
  metadata: object

SourceFetchResult
  items: SourceItemDraft[]
  next_cursor: string | null
  metadata: object
```

其中 `published_at` / `captured_at` 在 JSON-like payload 中使用可序列化时间字符串；后续 core 可以在转换内部对象时再映射为 datetime。

### 6. `notification.send` 第一版覆盖文本消息与最小审计字段

`notification.send` 第一版 SHOULD 定义：

- `NotificationSendInput`
- `NotificationSendResult`

并至少覆盖：

- 文本消息发送
- `channel`
- `severity`
- `metadata`

V1 不进入富媒体附件、复杂模板、交互式卡片或多厂商 channel 特有字段。其目标是先让通知插件能以统一方式表达“发什么、发到哪类通道、结果如何”。

建议的最小字段如下：

```text
NotificationSendInput
  channel: string
  text: string
  severity: string | null
  recipient: string | null
  metadata: object

NotificationSendResult
  accepted: boolean
  provider_message_id: string | null
  retryable: boolean
  metadata: object
```

`accepted=false` 只用于表达 provider 明确拒收、限流或临时不可投递等可被业务记录的发送结果。插件异常、配置缺失、payload 校验失败和运行时失败继续走 Runtime V1 结构化 `PluginError`。

### 7. 插件返回 draft / result，core 决定内部对象转换

Plugin IO DTO V1 SHALL 明确：

- 插件不得直接返回 ORM model、DB row、Repository object、内部 service object 或不可序列化对象。
- source 插件返回 `SourceItemDraft` 集合或等价 fetch result。
- notification 插件返回发送结果 DTO。
- core 后续再将这些 DTO 转为 `RawEvent`、`NotificationLog`、`AuditLog` 或其他内部对象。

这条边界是为了保证插件作者不需要知道数据库 schema，也避免插件 DTO 和 core 内部模型发生硬耦合。

### 8. 错误沿用 Runtime V1 结构，不新增第二套协议

Plugin IO DTO V1 SHALL 继续沿用 Runtime V1 已有的结构化错误形状：

- `code`
- `message`
- `stage`
- `retryable`
- `details`

本 change 不再额外设计第二套 capability-specific error envelope。typed DTO 应与现有错误边界兼容，而不是平行新增一套错误协议。

### 9. DTO 必须可校验、可序列化、可审计、可脱敏

typed DTO SHOULD 满足：

- 能校验必填字段、基础字段类型和 JSON-safe 值
- 能转换为 JSON-like 结构供 API、worker 或测试 harness 消费
- metadata 可以承载可审计字段
- 不强制暴露 secret、token、cookie、私有 URL 查询串或本地私有路径

source / notification DTO 中如出现潜在敏感字段，后续实现必须有脱敏或受控保留策略，但本 change 先把“不允许泄露”的边界写清。

## 风险与取舍

- [风险] typed DTO 和通用 transport 的分层不清，后续实现者可能直接在 runtime 中写 capability 分支。
  -> 缓解：design 明确 transport 保持通用，typed DTO 通过 helper / adapter 挂接，不把 runtime 变成业务分发表。

- [风险] `SourceItemDraft` 字段过多，提前把 source 特化场景冻死。
  -> 缓解：V1 只定义最小公共字段与 metadata，source-specific 细节后续增量扩展。

- [风险] Notification V1 只覆盖文本消息，后续很快遇到富消息需求。
  -> 缓解：V1 明确保留 metadata 与 channel/severity 承载面，但不提前把复杂模板系统带进来。

- [风险] 沿用 dataclass 可能让运行时校验能力偏弱。
  -> 缓解：本轮优先稳定契约和边界；如后续确实需要更强验证，可在不破坏 DTO 语义的前提下补 helper / schema。
