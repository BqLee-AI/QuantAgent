# Notification 插件边界参考

## 文档目的

本文面向 QuantAgent 仓库开发者，结合当前实现说明 `notification` 类型插件在系统里的职责边界、接入机制和常见误区。重点以官方 `Discord Notification` 插件为例，说明什么是合理的平台职责，什么会让插件机制退化成“主程序内建集成”。

当前分析基于以下真源：

- `plugins/notifications/discord/**`
- `packages/plugin-sdk/src/quantagent/plugin_sdk/**`
- `packages/core/src/quantagent/core/runtime/**`
- `packages/core/src/quantagent/core/events/**`
- `apps/api/src/quantagent/api/services/notification_ingress.py`
- `docs/design/02-core-architecture-and-runtime.md`
- `docs/design/03-plugin-system-and-registry.md`
- `docs/design/05-agent-workflow-design.md`

## 先说结论

- 旧的 `discord_interactions.py` 方向确实会让宿主看起来像内建 Discord；当前实现已经把它收敛为通用 `notification_ingress.py` host。
- 现在 API 宿主只保留通用 notification ingress 职责：读取原始请求、构造 `NotificationReceiveInput`、调用 orchestration、按插件返回的状态码与 response 透传。
- Discord 的公钥、allowlist、响应文本和错误语义都留在插件层与插件配置层，不再留在 `apps/api`。
- 这说明通知插件链路已经从“部分插件化”进一步收敛为“宿主通用、协议在插件”的模型。
- 合理方向不是把 webhook ingress 全丢给插件，而是把 API 层收敛成 **通用 ingress 宿主**，由插件负责渠道协议适配，由平台负责 invoke、审计、持久化、事件发布和后续审批/通知链路衔接。

## Notification 插件在 QuantAgent 里的职责边界

根据 `docs/design/03-plugin-system-and-registry.md`，`notification` 插件的核心职责是：

- 发送通知或展示提醒。
- 适配具体渠道协议，例如 Discord、Telegram、Email、UI。
- 在需要双向交互的渠道中，把外部回调或文本输入标准化为平台可处理的接收结果。

不应该让 notification 插件负责的事情：

- 自己发现或注册自己。
- 直接持有 Event Bus publisher。
- 直接写数据库、写审批记录、写审计记录。
- 绕过 AgentRuntime、Policy Gate、Approval 流程。
- 直接决定收到用户输入后系统状态如何变化。

平台层应该负责的事情：

- 扫描 `plugin.yaml`，建立 Registry 视图。
- 按 capability 调用插件。
- 保存配置、secret reference、启停状态和审计。
- 在插件返回标准化结果后，决定是否发布 topic、写 `ApprovalInput`、触发后续流程。

## 插件如何通过 manifest + capability 接入

当前 Discord 插件通过 `plugin.yaml` 接入：

```yaml
id: quantagent.official.notification.discord
type: notification
entrypoint: src.discord_plugin:plugin
capabilities:
  - notification.send
  - notification.receive
```

这条链路在 QuantAgent 中应当分成四层：

```text
plugin.yaml
  -> PluginRegistry
  -> PluginRuntimeService
  -> plugin-sdk DTO
```

各层职责：

- `plugin.yaml`
  只声明插件元信息、entrypoint、capability、config schema。
- `PluginRegistry`
  只负责扫描、校验和查询 `PluginRecord`，不执行插件代码。
- `PluginRuntimeService`
  根据 manifest entrypoint 加载插件、执行 `load/start/invoke/stop`。
- `plugin-sdk DTO`
  约束 `notification.send` / `notification.receive` 的输入输出结构。

当前代码里已经落地的关键边界：

- API 通过 `PluginRegistry.get_plugin(...)` 找插件，不直接 import Discord 模块。
- Runtime 通过 `PluginRuntimeService.invoke(...)` 按 capability 调用插件。
- Discord 插件只接收 `RuntimeContext.config` 和 invoke input，不直接拿 API Request、DB session 或 Event Bus。

## `notification.send` / `notification.receive` 的运行机制

### `notification.send`

当前 `plugin-sdk` 中，发送链路使用：

- 输入 DTO：`NotificationSendInput`
- 输出 DTO：`NotificationSendResult`

合理职责分配：

```text
平台业务流程
  -> 选择 notification 插件
  -> Runtime invoke(capability="notification.send")
  -> 插件把平台输入映射成渠道请求
  -> 插件返回 accepted / retryable / metadata
  -> 平台决定是否记审计、更新状态、发布 notification.completed
```

插件应该做：

- 校验消息内容是否满足渠道协议。
- 解析 secret reference。
- 调用 Discord webhook / Telegram API / Email provider。
- 把渠道返回值标准化。

插件不应该做：

- 自己发布 `notification.completed`。
- 自己修改事件状态。
- 自己决定审批是否完成。

### `notification.receive`

当前 `plugin-sdk` 中，接收链路使用：

- 输出 DTO：`NotificationReceiveResult`
- 内含标准化条目：`NotificationReceiveItem`

当前 DTO 语义表明，`notification.receive` 更像：

```text
外部渠道 ingress
  -> 宿主拿到原始 HTTP 请求
  -> Runtime invoke(capability="notification.receive")
  -> 插件完成渠道协议校验和规范化
  -> 返回 response + item
  -> 宿主把 response 回给上游渠道
  -> 宿主决定 item 进入哪条业务链路
```

`NotificationReceiveResult` 当前承担两件事：

- `response`
  返回给外部平台的 HTTP body，例如 Discord `PING` 的 `PONG`。
- `item`
  平台内部要处理的标准化用户输入。

这说明 receive 插件本质上是 **渠道协议适配器**，不是业务流程终点。

## 平台层、插件基类/DTO、runtime invoke、topic/event bus、HTTP ingress 各自该做什么

## 平台层

平台层包括 `apps/api`、Registry、Runtime、后续的审批/审计/持久化服务。

应该做：

- 终止 HTTP 请求，读取原始 body 和头。
- 根据路由或绑定关系确定候选插件。
- 校验插件是否声明了 `notification.receive` 或 `notification.send`。
- 调用 runtime。
- 对插件输出做结构校验。
- 把标准化结果交给审批、通知、审计、事件链路。

不该做：

- 理解 Discord slash command 的字段结构。
- 维护 Discord 专用结果码体系。
- 为每个通知通道复制一套专属 service、settings 和 public route。

## notification 插件基类 / DTO

当前基类和 DTO 已经提供了合理边界：

- `BasePlugin`
  只提供 `load/start/stop/health_check/invoke` 生命周期和 `context`。
- `NotificationSendInput/Result`
  提供发送契约。
- `NotificationReceiveItem/Result`
  提供接收契约。

应该继续保持：

- 插件看到的是结构化 config 和 input。
- 插件返回 JSON-safe mapping。
- DTO 不携带 HTTP 框架对象、ORM model 或 Event Bus 对象。

## runtime invoke

`PluginRuntimeService.invoke(...)` 的职责应该始终是：

- 从 `PluginRecord` 加载 entrypoint。
- 创建 `RuntimeContext`。
- 按 capability 调用 `invoke(...)`。
- 将异常转成结构化 `PluginError`。

它不应该知道：

- Discord、Telegram 或 Email 的业务语义。
- 该结果是否要写 `ApprovalInput`。
- 该结果是否意味着自动批准、拒绝或执行。

## topic / Event Bus

`packages/core/src/quantagent/core/events/README.md` 已经定义得很明确：

- 插件不能直接发布事件。
- 平台在拿到插件标准化输出后，再构造 `EventEnvelope`。

对于通知链路，合理用法是：

- `notification.requested`
  平台决定要发送某条通知时发布。
- `notification.completed`
  某个通知插件发送完成后，由平台发布。
- 如果接收到的是用户回复、命令或审批输入，不应简单混成 `notification.completed`，而应进入更贴近业务的链路，例如：
  - `ApprovalInput`
  - 审批评估
  - 或未来明确设计过的新 topic

不合理用法：

- 让插件自己 publish event。
- 把 Discord interaction 当成 Event Bus 真源。
- 把 webhook 收到什么、系统状态就直接改成什么。

## HTTP ingress

HTTP ingress 存在于 API 层是合理的，因为：

- Discord webhook / interaction 本质是外部 HTTP 回调。
- 签名头、原始 body、状态码、超时和反向响应都属于 HTTP 宿主责任。
- 插件不能也不应该自己暴露公网监听端口。

但 API 层只应承接 **协议无关的 ingress 宿主职责**，不应承接 **Discord 业务内建逻辑**。

## 当前宿主模型

当前实现已经收敛为：

```text
POST /api/v1/integrations/notifications/ingress
  -> NotificationIngressHostService
  -> NotificationIngressService
  -> PluginRuntimeService.invoke(capability="notification.receive")
  -> 插件返回 response_status_code + response + item
  -> API 直接透传 response_status_code + response
```

这里的关键边界是：

- API 宿主只负责读取原始请求、构造 `NotificationReceiveInput`、传播 `request_id`。
- `packages/core` 只负责 plugin record 校验、runtime invoke 和 result 结构校验。
- Discord 插件自己负责验签、allowlist、payload 解析、HTTP 状态码和 response 生成。
- API 与 core 不再解释 Discord 私有码，也不再维护 Discord 专属 env 名称。

## 当前实现做对了什么

1. API host 已经通用化。
   宿主公开入口是 `/api/v1/integrations/notifications/ingress`，不再以 provider 名称进入路由真源。

2. 插件配置边界收回到插件层。
   Discord 的 `public_key`、`response_text`、allowlist、timestamp tolerance 都通过 `NOTIFICATION_INGRESS_PLUGIN_CONFIG` 传入。

3. HTTP 结果语义由插件负责。
   `NotificationReceiveResult` 现在显式携带 `response_status_code`，host 只透传，不理解 provider 私有码。

4. 调用链仍然符合 manifest + registry + runtime 模型。
   API 通过 Registry 找插件，Runtime 按 capability 调用，不直接 import 具体插件实现。

## 当前仍然缺什么

### 1. 只实现了 HTTP host

虽然 `NotificationReceiveInput.transport` 已经为 webhook、websocket、polling 留了模型，但当前只实现了 Discord 所需的 HTTP host adapter。websocket host、polling host 和对应 lifecycle 仍然是后续 change。

### 2. receive record / audit / approval handoff 还没落地成持久真源

当前 ingress 成功后，`NotificationReceiveItem` 还没有进入稳定的数据库 record、审计记录或审批回流链路。这部分边界已在 OpenSpec 中说明，但实现还停留在 host + orchestration + plugin contract。

### 3. 目前还是单 endpoint 绑定

`NOTIFICATION_INGRESS_PLUGIN_ID` 仍然是当前 API host 的单绑定入口。后续如果要支持多 provider、多 endpoint、多租户或更复杂的 route binding，需要独立设计 ingress binding 模型，而不是在当前 host 上继续堆平台特例。

## 开发通知插件时的原则

1. 任何平台专属适配都只放在插件里。
   包括签名、challenge、payload 解析、provider-specific HTTP 状态码和 response body。

2. API host 只处理 transport host，不处理 provider business semantics。
   宿主可以读取 HTTP headers/body/query/path，也可以未来扩展 websocket / polling host，但不能理解某个平台的私有码或字段语义。

3. `packages/core` 只负责平台编排，不负责 provider 适配。
   它可以校验 capability、校验 DTO、触发后续审计/record/topic，但不能写死 Discord、Slack、Telegram 的规则。

4. 插件返回值必须完整表达对宿主的响应需求。
   对 `notification.receive` 来说，这意味着插件需要返回：
   - `accepted`
   - `code`
   - `message`
   - `response_status_code`
   - `response`
   - 可选 `item`

## 后续扩展建议

- 如果接入 websocket / gateway 型平台，新增 transport host，而不是回到 `apps/api` 新建 `<provider>_interactions.py`。
- 如果要支持多 ingress binding，把“endpoint -> plugin_id -> plugin_config”建成平台绑定模型，而不是继续扩环境变量名。
- 如果要让 receive 结果进入审批、重分析或执行链路，应该在 core 增加 receive record / audit / topic / approval handoff，而不是让 notification 插件直接写业务状态。

这样 API 仍然保留公网 ingress 职责，但不再直接内建 Discord 业务配置。

## 方向二：把渠道配置回收到插件配置体系

优先级最高的收敛点：

- `public_key`
- `response_text`
- `timestamp_tolerance_seconds`
- `guild_allowlist`
- `channel_allowlist`

这些字段应该优先来自插件配置或平台管理的插件 effective config，而不是 `apps/api` settings。

API 层只保留真正宿主级的入口开关，例如：

- 是否启用某个 ingress
- ingress path 或 binding
- 是否允许匿名公网访问该入口

## 方向三：把 receive 结果接入平台主链路

对 `NotificationReceiveItem` 的合理后续处理应是：

```text
receive item
  -> 写审计
  -> 规范化为 ApprovalInput / command input / human message input
  -> 触发审批评估或业务路由
  -> 按需要发布 topic
```

不要停在“回了 Discord 200 + JSON response”。

## 方向四：收敛 capability 级错误契约

长期建议把 receive 场景的错误码分为两类：

- 平台通用码
  - 例如 `SIGNATURE_INVALID`、`PAYLOAD_INVALID`、`UNSUPPORTED_EVENT_TYPE`
- 插件私有码
  - 放在 metadata，供日志和诊断使用

这样宿主只理解 capability 级公共语义，不理解 Discord 私有枚举。

## Event Bus / topic 在通知链路里的合理使用方式

## 发送链路

推荐：

```text
Decision / Approval service
  -> publish notification.requested
  -> notification dispatcher 选择插件并 invoke(notification.send)
  -> 平台记录结果
  -> publish notification.completed
```

## 接收链路

接收链路不要简单等同于 `notification.completed`。更合理的是：

```text
external webhook ingress
  -> invoke(notification.receive)
  -> 得到 NotificationReceiveItem
  -> 转成 ApprovalInput 或其他平台输入对象
  -> 审批/命令服务继续处理
  -> 必要时发布 approval.* 或未来定义的新 topic
```

关键点：

- Event Bus 用于解耦平台模块，不用于让插件自己驱动主流程。
- topic 是平台语义，不是 Discord 协议语义。
- Discord 的 `PING`、slash command、guild/channel allowlist 都不应该变成核心 topic 名。

## 如何开发一个新的通知插件

建议步骤：

1. 在 `plugins/notifications/<name>/` 下创建插件目录。
2. 编写 `plugin.yaml`，声明：
   - `id`
   - `type: notification`
   - `entrypoint`
   - `capabilities`
   - `config_schema`
3. 编写 `config.schema.json`，只声明插件自己的配置契约和 secret reference。
4. 基于 `BasePlugin` 实现 `invoke(...)`。
5. 对发送能力实现 `notification.send`：
   - 读取 `NotificationSendInput`
   - 调用渠道 API
   - 返回 `NotificationSendResult`
6. 如果渠道有回调输入，再实现 `notification.receive`：
   - 从 invoke input 读取原始 headers/body
   - 完成渠道验签和协议解析
   - 返回 `NotificationReceiveResult`
7. 为插件写独立测试，不依赖 API。
8. 如果需要公网回调，再在宿主补最小 ingress 适配，但保持它是通用宿主，而不是把渠道业务写死在 API。

开发新通知插件时的判断标准：

- 如果离开 API 路由后，核心逻辑仍然主要在插件里，方向通常是对的。
- 如果为了支持一个新渠道，需要先在 API settings、router、service 里新增一大组 `<CHANNEL>_*` 配置和分支，说明边界已经开始漂移。

## 以 Discord 为例：哪些属于通用模式，哪些只是 Discord 特例

## 通用模式

这些模式适用于大多数 notification 插件：

- 通过 manifest 注册为 `notification` 类型插件。
- 用 capability 区分发送和接收。
- 发送路径通过 `NotificationSendInput/Result` 标准化。
- 接收路径通过 `NotificationReceiveResult` 返回：
  - 给上游渠道的 HTTP response
  - 给平台内部的标准化 `item`
- 外部 webhook ingress 由 API 宿主终止。
- 插件只做渠道协议适配，不直接写平台状态。

## Discord 特例

这些是 Discord 专用实现细节，不应上升为平台共性：

- `Ed25519` 签名头：
  - `X-Signature-Ed25519`
  - `X-Signature-Timestamp`
- `PING` / `PONG` 握手语义。
- `APPLICATION_COMMAND` payload 结构。
- ephemeral response 格式和 `flags=64`。
- guild/channel allowlist 的字段位置和判断逻辑。
- 从 `data.options` 里抽取 `text/message/content/prompt`。

平台可以承认这些特例存在，但不应该把这些特例扩散成 API 公共抽象或核心运行时抽象。

## 对当前 Discord 插件机制的判断

可以把当前状态概括为：

- **插件化程度合格但不完整**：
  插件本体、manifest、runtime invoke、DTO 边界都已经在正确方向上。
- **宿主特化偏重**：
  API 入口、配置和错误映射仍然是 Discord 专属。
- **主流程尚未接通**：
  `notification.receive` 产出的 `item` 还没有进入审批、审计、持久化或事件链路。

因此，当前实现更适合作为：

- `notification.receive` capability 的最小探路实现；
- Discord 通道实验版本；
- 平台后续通用 notification ingress 设计的反例和参考。

不适合作为：

- 长期稳定的 notification 插件宿主模式；
- 多通知渠道扩展的模板；
- “插件机制已经完成”的证据。

## 本轮建议沉淀

后续如果继续推进通知插件机制，建议优先补一份更稳定的真源，至少覆盖：

- 通用 notification ingress / receive 设计。
- `NotificationReceiveItem` 进入 `ApprovalInput` 或其他平台输入对象的映射规则。
- receive capability 的平台通用错误语义。
- 通知发送与接收链路的审计字段和 topic 使用规则。
