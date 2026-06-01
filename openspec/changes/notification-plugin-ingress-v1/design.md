## Context

当前仓库已经存在一条最小可运行的通知插件链路：

- `plugins/notifications/discord/plugin.yaml` 让官方 Discord 插件进入 Registry。
- `packages/core/src/quantagent/core/runtime/service.py` 能按 manifest entrypoint 动态加载插件，并通过受控 `RuntimeContext` 调 `invoke(...)`。
- `packages/plugin-sdk/src/quantagent/plugin_sdk/io.py` 已经定义：
  - `NotificationSendInput`
  - `NotificationSendResult`
  - `NotificationReceiveItem`
  - `NotificationReceiveResult`
- `apps/api/src/quantagent/api/services/discord_interactions.py` 已能接收 Discord HTTP webhook，并把请求转发给 Discord 插件的 `notification.receive` capability。

所以现在的问题不是“插件机制能不能加载通知插件”，而是“通知插件如何成为对多渠道可扩展的宿主模型，而不是每个渠道都在 API 宿主里写一套特例”。

从当前实现看，存在三个结构性空洞：

1. **`notification.receive` 缺 typed input。**  
   现在 receive 方向只有 output DTO，没有像 `source.fetch` / `notification.send` 那样稳定的 receive input contract。宿主和插件之间只能通过 ad hoc mapping 约定 `headers`、`body` 等字段。

2. **API ingress 还是 Discord 专属宿主。**  
   现有 `discord_interactions.py` 已经把 Discord 专属 settings、header 名称、错误码和公开 route 语义固化在 API 层，导致“动态插件加载”与“宿主内建 Discord 集成”并存。

3. **receive 结果没有进入平台主链。**  
   `NotificationReceiveResult.item` 现在只存在于插件返回值里，没有稳定的平台侧 notification receive record / audit / topic / approval input 边界。

本 change 的设计目标，是把这三层边界收住，同时尽量不扩大到消息会话、完整审批系统或所有通知渠道一次性实现。

还需要补一个关键前提：通知平台的接入方式并不都一样。

- Discord 当前是 HTTP interaction webhook。
- 有的平台是 websocket / gateway / 长连接事件流。
- 还有的平台要求轮询消息或事件状态。

所以模型不能写死成“notification receive == webhook route”，但本轮实现范围仍然只做 Discord 所需的基础 HTTP 接口。

## Goals / Non-Goals

**Goals:**

- 定义 Notification Plugin Ingress V1 的宿主分层和调用链。
- 给 `notification.receive` 补一套 typed input 合同方向。
- 明确 API / core / plugin-sdk / notification plugin 的职责边界。
- 让 Discord 成为第一个合规样板，而不是继续作为 API 宿主里的特例真源。
- 为后续 Telegram、Slack、Email inbound webhook、自定义 webhook 通道保留一致接入方式。

**Non-Goals:**

- 不在本轮引入完整 message / session / thread 领域模型。
- 不在本轮实现完整审批回流和自动执行。
- 不在本轮增加新的 plugin type。
- 不让插件直接持有 DB session、Event Bus publisher、审批 service 或 secret resolver。
- 不把所有 webhook / callback 都抽成超通用可配置框架；V1 只收住边界和样板能力。

## Architecture

Notification Plugin Ingress V1 建议采用四层结构：

```text
transport host (http / websocket / polling)
  -> core notification ingress orchestration
  -> plugin runtime invoke(notification.receive)
  -> plugin receive adapter result
  -> core orchestration decides audit / record / topic / approval handoff
```

更具体地说：

```text
transport-specific ingress
  -> host adapter
  -> NotificationIngressRequest DTO
  -> NotificationIngressService (core-owned orchestration)
  -> PluginRegistry lookup
  -> PluginRuntimeService.invoke(capability="notification.receive")
  -> NotificationReceiveResult
  -> NotificationReceiveRecord / audit / topic publish / approval input handoff
  -> transport-specific response / ack / no-op
```

关键原则：

- host adapter 只终止 transport 协议，不理解渠道业务语义。
- 插件只做渠道协议适配，不改平台业务状态。
- core 层负责 orchestration、审计、topic 和后续业务衔接。

## Decisions

### 1. transport host 模型要可扩展，但本轮只实现 HTTP ingress

Notification Plugin Ingress V1 的架构目标必须允许以下 host adapter 共存：

- HTTP webhook host
- websocket / gateway host
- polling / scheduled host

它们的共同点应是：

- 负责接住 transport 协议
- 负责把外部输入规整成平台 typed ingress request
- 调用统一 orchestration

它们的不同点应由 transport adapter 自己承担：

- HTTP 状态码与 body
- websocket ack / event loop / reconnect
- polling interval / cursor / checkpoint

本轮实现边界：

- 只实现 Discord 所需的 HTTP host adapter
- 不实现 websocket host
- 不实现 polling host

### 2. API 层保留 HTTP ingress host，但从 Discord 专属 service 收敛为通用宿主

API 层仍然要承接公网 HTTP ingress，这是 HTTP 宿主边界，不应该要求插件自己暴露监听端口。

但 API 层长期只做以下事情：

- 读取原始 body
- 读取 headers / query / path params
- 生成 request id
- 调用平台的 notification ingress orchestration
- 把 orchestration 的标准化 response 映射回 HTTP response

API 层不再长期承担：

- Discord-specific payload 解析
- Discord-specific settings 作为平台真源
- Discord-specific failure semantics 作为 API 私有逻辑
- 每个渠道各自一份 `<channel>_interactions.py` 宿主 service

实现收敛策略：

- `apps/api` 只暴露通用 `/api/v1/integrations/notifications/ingress` HTTP host
- 宿主不再保留 Discord 专属 route 或 service 文件
- 宿主不再维护 Discord 专属 settings 名称，也不解释 Discord 专属错误码
- Discord 需要的签名、公钥、allowlist、响应文本等都通过插件配置传入

### 3. `plugin-sdk` 需要新增 `NotificationReceiveInput`

当前 `NotificationReceiveResult` 已足够表达：

- 接收是否成功
- 给外部平台返回的 response
- 标准化的 receive item

但缺少宿主到插件的 typed input。

V1 建议新增：

```text
NotificationReceiveInput
  transport: string
  headers: object
  body_text: string | null
  body_base64: string | null
  query_params: object
  path_params: object
  request_metadata: object
  config_override: object | null
```

设计要点：

- 它表达“宿主已经安全整理过的 transport ingress 数据”
- 不直接暴露 FastAPI `Request` / `Response`
- 只允许 JSON-safe 值
- 对 body 提供稳定、安全的表达，而不是把 Python bytes / request object 直接传给插件

其中 `transport` 字段的目的，是明确这条输入来自哪种宿主模型，例如：

- `http.webhook`
- `websocket.gateway`
- `polling.fetch`

这样 future channel adapter 可以在不改 orchestration 总体结构的情况下扩展。

为什么同时保留 `body_text` 和 `body_base64` 方向：

- 大多数通知 webhook 都是 UTF-8 文本，`body_text` 足够
- 少数签名 / binary callback 场景可能需要原始字节等价表示，`body_base64` 为未来留 seam
- 第一版 Discord 实现可只使用 `body_text`

### 4. `packages/core` 需要引入 notification ingress orchestration

当前 API 层直接负责：

- 查 Registry
- 调 Runtime
- 验证 plugin result
- 映射 HTTP response

这在 demo 阶段可接受，但长期属于错误分层，因为：

- API 私有 service 很快会按渠道横向复制
- 审计 / record / topic / approval handoff 没有统一边界
- 插件结果的业务含义被分散在 route / service 中

因此需要一个 core-owned orchestration，暂称：

```text
NotificationIngressService
```

它的职责应至少包括：

- 校验 plugin record 合法性
- 校验 plugin capability
- 构造 typed `NotificationReceiveInput`
- 调用 runtime
- 校验 `NotificationReceiveResult`
- 产出标准化 orchestration result
- 决定审计、记录、topic、审批衔接

API 只依赖它，而不再自己理解 Discord 语义。

### 5. receive 结果进入平台主链前，先落统一 receive record / audit

当前 `NotificationReceiveResult.item` 一旦成功，就只在 HTTP request 生命周期中暂存，没有持久对象。

V1 不要求立即接完整审批系统，但至少要收住“平台先生成统一 receive record / audit，再决定下一步”的方向。

建议的最小平台对象：

```text
NotificationReceiveRecord
  id
  plugin_id
  transport
  external_interaction_id
  source_id
  text
  payload_summary
  metadata
  received_at
  request_id
  correlation_id
  processing_status
```

为什么先定义 record，而不是直接写 `ApprovalInput`：

- 并非所有通知 receive 都是审批
- Telegram / Slack / Email inbound 可能是“确认收到”、“补充说明”、“命令调用”、“重分析请求”
- 统一 receive record 能给 audit、replay、后续业务分流留出真源

### 6. Event Bus 的使用边界必须保持平台发布、插件不发布

Notification receive 如果要进入事件总线，必须由平台编排层发布。

推荐方向：

- `notification.requested`：平台请求某个 notification plugin 发送消息
- `notification.completed`：平台完成发送结果登记
- `notification.received`：平台已标准化接住一条外部通知输入

这里有一个重要边界：

- `notification.received` 不是审批完成
- `notification.received` 不是业务动作执行完成
- 它只是平台 ingress 标准化成功的事实

之后是否转成：

- `approval.requested`
- `approval.completed`
- `decision.created`
- `runtime.failed`

由 core 业务编排决定，而不是由 Discord 插件决定。

### 7. Discord 的合规改造目标：协议仍在插件，HTTP 宿主只做通用 host

Discord 样板的目标状态：

- `plugins/notifications/discord/**` 继续负责：
  - webhook 发送
  - interaction 验签
  - `PING`
  - command payload 解析
  - response 构造
- API ingress host 只负责把 HTTP callback 转成 `NotificationReceiveInput`
- core orchestration 负责：
  - plugin invoke
  - receive record / audit
  - topic / approval handoff

因此，Discord 改造不是“把 route 挪进插件”，而是：

- 保留 HTTP ingress 在 API
- 把 Discord-specific 宿主逻辑抽空
- 把 Discord-specific 协议逻辑继续收回插件
- 把编排逻辑提升到 core

### 8. 第一版不引入 websocket / polling host 的完整实现

尽管模型要支持 websocket / polling 扩展，但本轮不实现：

- websocket gateway client
- reconnect / heartbeat / subscription lifecycle
- polling schedule / cursor checkpoint / rate-limit coordinator

原因：

- 这些能力都不是 Discord 当前基础接口所必需
- 它们会把范围扩到 worker / scheduler / runtime lifecycle / state recovery
- 现在先把可扩展边界和 typed contract 收住更重要

### 9. 第一版不引入统一聊天会话领域

为什么这轮不做 chat/session：

- 当前主要痛点是 ingress host 与插件边界失真
- 一旦引入 chat/session，会连带：
  - 参与者身份
  - 线程状态
  - 消息持久化
  - UI 会话
  - 授权与幂等
  一起进场

这会严重扩大范围，且当前仓库没有足够真源支撑这一刀。

因此本轮只收住：

- receive input/output DTO
- ingress orchestration
- receive record / audit / topic 边界

## Proposed Types / Boundaries

### `packages/plugin-sdk`

新增 / 扩展方向：

- `NotificationReceiveInput`
- 保持：
  - `NotificationSendInput`
  - `NotificationSendResult`
  - `NotificationReceiveItem`
  - `NotificationReceiveResult`

契约要求：

- JSON-safe
- frozen/readonly 语义
- 可直接用于测试构造
- 不暴露 host framework objects

### `packages/core`

新增方向：

- `NotificationIngressService`
- `NotificationReceiveRecord` 的 service / repository / audit 边界
- 可选 `NotificationEventPublisher` 或 orchestration 内的 event publish seam

不做：

- 在插件运行时暴露 event bus
- 在 API 层直接持久化业务状态

### `apps/api`

新增/调整方向：

- `NotificationIngressHttpResult` 一类的通用 HTTP 映射结果
- 通用 ingress dependency / service getter
- 路由层不直接持有 Discord 专属业务语义

### `plugins/notifications/*`

每个插件都应围绕同一模式：

- manifest 声明 `notification.send` / 可选 `notification.receive`
- config schema 只声明渠道配置和 secret reference
- send/receive 协议实现完全在插件内
- receive 使用 typed `NotificationReceiveInput`

## Failure Model

### API / host failures

- route 未启用
- plugin id 缺失
- plugin record 不存在 / 不合法
- runtime invoke 失败

这些失败由宿主 / orchestration 统一映射为结构化 HTTP 失败或业务失败。

### Plugin protocol failures

- signature invalid
- timestamp invalid
- unsupported event type
- malformed payload
- missing channel / guild allowlist

这些失败由插件标准化返回 `NotificationReceiveResult`，再由 orchestration 做后续映射。

### Business-chain handoff failures

- receive record 写入失败
- audit 写入失败
- topic publish 失败
- approval handoff 失败

这些失败不应再由插件决定；它们属于平台后半段失败，必须进入 core 的结构化错误和审计链。

## Risks / Trade-offs

- [风险] `NotificationReceiveInput` 如果设计过宽，会逼插件作者处理很多不相关字段。  
  缓解：V1 只保留最小 HTTP ingress 形状，不引入 session / actor / auth 等更高层对象。

- [风险] 提前定义 `notification.received` 可能扩大 topic 集合。  
  缓解：在 spec 中明确它的语义和发布责任，仅平台 orchestration 可发。

- [风险] 目前只落地了 HTTP host，websocket / polling transport 仍未实现。  
  缓解：DTO 与 orchestration 已保留 `transport` 字段和通用 host 模型，本轮严格限制在 Discord 所需的 HTTP 基础接口。

- [风险] receive record 命名和最终持久化结构可能后续演化。  
  缓解：本轮只固定边界和语义，不强行冻结所有 DB 字段。

## Migration Plan

1. 先完成本 change 的 OpenSpec-only PR。
2. 维护者认可后，先改 `plugin-sdk`，补 `NotificationReceiveInput` 和相关测试。
3. 再改 `packages/core`，引入 notification ingress orchestration 和 receive record / audit 边界。
4. 再改 `apps/api`，把 Discord 专属 ingress service 收敛到通用 host。
5. 最后修改 Discord 插件和测试，使其以新 typed input 和 orchestration 方式运行。

## Open Questions

- `notification.received` 是否在第一版就进入默认 Event Bus topic 集合，还是先只作为 core 内部 record/audit 事实？
- receive record 是先做内存/服务层边界，还是直接进入数据库持久化 change？
- 一个 ingress route 在第一版是否需要支持多 plugin binding，还是先固定一条 route 绑定一个 plugin？
