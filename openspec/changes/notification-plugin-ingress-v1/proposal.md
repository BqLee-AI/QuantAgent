## Why

当前仓库已经证明了第一版通知插件可以通过 Registry + Runtime 动态加载，并在插件边界内完成 Discord webhook 发送和 interaction 接收。但这条链路仍然存在两个结构性问题：

1. **跨平台扩展边界没有收住。**
   现有 `plugin-sdk` 只为 `notification.send` 定义了稳定 input/output DTO，而 `notification.receive` 只有 output，没有宿主与插件之间稳定的 receive input 契约。这样继续接 Telegram、Slack、Email inbound webhook、企业微信机器人、Web UI callback，甚至需要 websocket、长连接 gateway 或 polling 才能接入的平台时，宿主层很容易继续为每个平台发明不同的 route、不同的 transport 适配和不同的 invoke input 形状，导致“看起来是插件，实际上每个平台都在主程序里半内建”。

2. **Discord 仍然是半内建集成。**
   当前 `apps/api/src/quantagent/api/services/discord_interactions.py` 虽然没有直接 import Discord 插件实现，仍然通过 `PluginRegistry` + `PluginRuntimeService` 调 `notification.receive`，但 API 宿主中已经固化了 Discord 专属 ingress 路径、配置项、header 提取和错误语义。这会让后续渠道继续复制同样的宿主特化代码，也会让“通知插件只做渠道协议适配，平台负责后续编排”的长期边界越来越模糊。

如果不先把这条边界收住，后续通知渠道接入会出现以下问题：

- API 层为每个渠道复制一套 webhook ingress service。
- `packages/plugin-sdk` 无法提供统一 receive contract，插件作者各自约定入站 payload。
- `packages/core` 无法沉淀统一的 notification receive orchestration、审计、持久化和 topic 发布路径。
- Discord 当前的 receive 结果继续停留在“收到 HTTP 请求并返回 HTTP 响应”，而不是进入审批、通知记录和事件链路。

本 change 先不实现所有渠道，也不直接改完整审批链，而是先在 OpenSpec 中收住 **Notification Plugin Ingress V1** 的目标边界：让 API、core、plugin-sdk 和 notification 插件各司其职，并以 Discord 作为第一个合规改造样板。

## What Changes

- 定义 Notification Plugin Ingress V1 的分层边界，明确 `apps/api`、`packages/core`、`packages/plugin-sdk` 和 `plugins/notifications/*` 各自需要暴露什么、不能暴露什么。
- 为 `notification.receive` 增加稳定的 typed input 合同方向，使宿主与插件之间不再依赖 Discord 专属 ad hoc mapping。
- 定义通用 notification transport host 语义：HTTP ingress 仍然存在于 API 层，但模型本身需要支持 webhook、websocket、polling 等不同 transport 的扩展；本轮实现只落 Discord 需要的基础 HTTP ingress。
- 定义平台侧 notification receive orchestration 边界：插件返回 receive result 后，由平台决定持久化、审计、topic 发布和审批编排，而不是让插件或 API route 直接承担业务状态流转。
- 以 Discord 为例，收敛第一版实现方向：Discord 的发送与接收协议处理都保留在插件内部；API 宿主改为调用通用 ingress orchestration，而不是使用 Discord 专属 service 作为长期真源。

## Capabilities

### New Capabilities

- `notification-plugin-ingress-v1`: 定义 QuantAgent 通知插件的入站与出站宿主边界、typed receive contract、平台编排语义和可扩展接入模型。

### Modified Capabilities

- `plugin-io-dto-v1`: 从当前仅稳定 `notification.send`，扩展到为 `notification.receive` 提供第一版 typed input/output contract。
- `discord-experimental-plugins`: Discord 插件从“动态加载但宿主半内建”的实验形态，收敛为 Notification Plugin Ingress V1 的第一个合规实现样板。
- `discord-interaction-webhook-ingress`: 从 Discord 专属 ingress service，收敛到通用 notification ingress host + Discord plugin adapter 的调用关系。
- `kafka-event-bus-v1`: 如需让 receive 结果进入统一主链，本 change 将定义 notification receive 后的平台 topic 使用边界，而不是由插件直接 publish。

## Impact

- `apps/api/src/quantagent/api/routers/v1/`
- `apps/api/src/quantagent/api/services/`
- `apps/api/src/quantagent/api/config/`
- `packages/core/src/quantagent/core/runtime/**`
- `packages/core/src/quantagent/core/events/**`
- `packages/plugin-sdk/src/quantagent/plugin_sdk/**`
- `plugins/notifications/**`
- `docs/design/03-plugin-system-and-registry.md`
- `docs/design/08-api-and-websocket-design.md`
- `docs/references/plugins/notification.md`

## Context

当前实现已经具备以下基础：

- 官方 notification 插件可通过 `plugin.yaml` 进入 Registry。
- Runtime V1 能根据 manifest 动态加载插件，并注入受控 `RuntimeContext`。
- `plugin-sdk` 已为 `notification.send` 提供稳定 typed DTO。
- Discord 插件已经同时承接 `notification.send` 和 `notification.receive` capability。
- API 已经能接住 Discord interaction webhook，并把请求转发给插件。

但当前链路中仍有三个明显空洞：

1. `notification.receive` 缺 typed input 合同。
   现在 plugin receive 侧依赖 `request.input["headers"]` / `request.input["body"]` 这类宿主与插件私下约定，缺少可复用、可测试、可向其他渠道推广的 receive input DTO。

2. API ingress 没有抽象成通用 notification ingress host。
   现在宿主层直接暴露 Discord 专属 settings 和 service，导致平台层无法为其他渠道复用这套结构。

3. receive 结果没有进入平台主链。
   插件返回的 `NotificationReceiveResult.item` 当前还没有清晰的平台编排落点。它既没有进入 `ApprovalInput`，也没有统一的 notification receive audit / record / topic 语义。

本 change 需要把这些边界先固定下来，避免后续随着渠道数量增长而继续沿着特例实现扩散。

## Goals / Non-Goals

**Goals:**

- 定义一个对多渠道可扩展的 notification ingress 模型。
- 明确 API 层只做通用 ingress 宿主，不直接内建渠道业务逻辑。
- 明确 `packages/core` 负责 notification receive orchestration、平台审计和事件衔接，不把这些职责塞进 API router 或插件。
- 为 `plugin-sdk` 增加 `notification.receive` typed input contract 的方向，避免 receive 继续依赖 ad hoc mapping。
- 以 Discord 为例，明确第一版合规改造的目标状态：收发协议都由插件处理，宿主只做通用 host 和编排。
- 为后续 Telegram、Slack、Email inbound webhook、企业微信、自定义 webhook，以及需要 websocket / polling 的渠道留出统一接入模式。

**Non-Goals:**

- 不在本 change 中一次性实现完整审批回流、自动执行或统一聊天会话系统。
- 不在本 change 中扩展新的 plugin type。
- 不要求第一版把所有 notification channel 都做出来。
- 不要求第一版实现 websocket transport host、gateway client、polling scheduler 或多 transport runtime 全量能力。
- 不让插件直接持有 Event Bus publisher、DB session、审批 service 或内部 secret resolver。
- 不在本 change 中直接设计群聊会话、富交互组件、Bot gateway、长连接 polling 等高阶渠道能力。
- 不把 notification 插件升级成 source、industry 或 strategy 的替代入口。

## Decisions

### Decision 1: 宿主模型要面向多 transport 扩展，但本轮只实现 Discord 需要的 HTTP ingress

Notification Plugin Ingress V1 的长期模型 SHALL 面向多种 transport 扩展，包括但不限于：

- webhook / HTTP callback
- websocket / gateway / long-lived stream
- polling / scheduled pull

但本轮实现范围 SHOULD 严格收缩为：

- Discord 需要的基础 HTTP ingress
- `notification.receive` / `notification.send` typed contract
- 通用 host / orchestration / plugin 边界

这样做的原因：

- 有些通知或交互平台不是 webhook-first，而是 websocket-first 或 polling-first。
- 如果现在把架构写死为“notification receive == HTTP webhook”，后续会再经历一次宿主模型改造。
- 但如果本轮就实现 websocket host、gateway runtime、polling coordinator，又会明显超出 Discord 所需的最小基础接口。

因此，V1 要求是 **模型可扩展，交付范围收缩**。

### Decision 2: API 层保留 HTTP ingress，但收敛为通用 notification ingress host

API 层 SHALL 保留对公网 HTTP callback 的承接职责，因为 webhook / interaction 天然属于 HTTP 宿主边界。但 API 层长期只负责以下通用职责：

- 接收原始 HTTP 请求。
- 提取原始 body、headers、query、path params 和基础 request metadata。
- 根据 route 绑定或配置定位目标 notification plugin。
- 调用平台侧 notification ingress orchestration。
- 将 orchestration 返回的标准化 response 映射为 HTTP 响应。

API 层 MUST NOT 长期内建以下渠道专属内容：

- Discord 专属配置集合成为平台唯一真源。
- Discord 专属 payload 解析。
- Discord 专属错误码解释成为 API 宿主的一般职责。
- 每新增一个渠道就在 API 层复制一套 `<channel>_interactions.py` 私有 service。

短期内允许 Discord 仍保留公开 route 形状，但该 route SHOULD 只作为绑定到通用 ingress host 的一层适配，而不是长期核心编排真源。

### Decision 3: `packages/plugin-sdk` 需要为 `notification.receive` 提供 typed input contract

Notification Plugin Ingress V1 SHALL 为 `notification.receive` 定义稳定的 typed input 方向，至少覆盖：

- `transport`
- `headers`
- `body_text` 或 `body_bytes` 的安全表达
- `query_params`
- `path_params`
- `request_metadata`
- 可选的 `config_override`

设计目标不是把所有 Web 框架对象暴露给插件，而是把宿主能安全提供的 HTTP ingress 数据转换成插件可消费的 JSON-safe DTO。

该 DTO MUST NOT 包含：

- FastAPI `Request`
- `Response`
- DB session
- Event Bus publisher
- secret resolver
- 原始 socket / transport 对象

这样做的原因：

- 让 Discord 之外的 webhook 型通知插件可复用同一 receive input contract。
- 让测试可以不依赖 FastAPI，而直接构造 typed receive input。
- 让 API 层与插件层之间的边界对齐 `source.fetch` / `notification.send` 已有的 typed DTO 风格。

### Decision 4: `packages/core` 需要新增平台侧 notification ingress orchestration

Core 层 SHOULD 负责 notification receive 的平台编排，而不是由 API 私有 service 长期各写各的。该编排层至少负责：

- 校验目标 plugin record 与 capability。
- 调用 runtime。
- 校验插件 receive result。
- 生成平台统一的 notification receive audit / record。
- 决定是否发布后续 topic。
- 决定是否将 receive item 交给审批、重分析或其他业务入口。

这样可以避免以下错误分层：

- Router 直接处理 plugin business result。
- 插件自己写审批记录。
- API route 直接理解 Discord slash command 等渠道专属语义。

### Decision 5: 插件继续只做渠道协议适配，不直接发布 topic 或改业务状态

Notification 插件的长期职责仍然是：

- 对 `notification.send`：把平台发送请求映射为渠道请求，再把渠道结果标准化返回。
- 对 `notification.receive`：把外部 callback / message / interaction 校验并标准化为 receive result 和 receive item。

Notification 插件 MUST NOT：

- 直接 publish Event Bus topic
- 直接写 `ApprovalRecord`
- 直接推进 `Decision` 状态
- 直接调用 broker

原因：

- 插件是渠道协议适配器，不是业务状态真源。
- 平台必须保持审计、权限和 Policy Gate 的统一控制。
- `kafka-event-bus-v1` 已明确 plugin runtime 不能直接访问 event bus。

### Decision 6: 平台需要为 notification receive 结果定义统一主链衔接语义

当前 `NotificationReceiveResult.item` 只停留在 DTO 层，没有稳定的主链位置。本 change SHALL 收住以下方向：

- 平台在 receive result 成功且存在 `item` 时，先写统一 receive audit / record。
- 后续平台再根据场景把它映射到审批输入、通知回执、重分析请求或其他业务入口。
- 如果需要进入 Event Bus，topic 应由平台发布，而不是插件发布。

建议的最小 topic 方向：

- `notification.requested`
- `notification.completed`
- 新增 `notification.received`

其中：

- `notification.received` 表示“平台已经接住并标准化了一个外部通知渠道输入”，不是“业务动作已经完成”。
- `approval.requested`、`approval.completed` 等 topic 仍由更上游的审批编排决定，不由 Discord 插件直接生成。

### Decision 7: transport host 与 orchestration 要分离

为了兼容未来的 websocket / polling 型平台，Notification Plugin Ingress V1 SHOULD 把：

- transport host
- notification ingress orchestration

视为两个不同层次的边界。

这意味着：

- HTTP route 只是某种 host adapter
- 未来 websocket gateway client 也只是另一种 host adapter
- polling scheduler 也只是另一种 host adapter
- 它们最终都向同一平台 orchestration 提交 typed receive input 或等价 ingress request

这样后续扩展不会逼迫我们复制 Discord 的 HTTP route service 结构。

### Decision 8: Discord 作为样板需要做合规改造，而不是继续扩大宿主特例

以 Discord 为例，目标状态应为：

- 发送逻辑继续留在 `plugins/notifications/discord/**`
- 接收逻辑中的验签、`PING`、command payload 解析、response 生成继续留在 Discord 插件
- API 层不再把 Discord 专属 settings / service 作为长期架构真源
- 宿主只构造 typed receive input，调用 notification ingress orchestration
- 编排层决定是否写 record / audit / topic / approval input

这意味着 Discord 需要从“动态插件 + 宿主特化入口”收敛为“通用 ingress host 下的渠道插件样板”。

### Decision 9: 第一版不把所有渠道抽象成统一聊天会话模型

本 change 明确不在第一版 Notification Plugin Ingress V1 中引入完整 chat/session/message thread 领域模型。

原因：

- 当前核心痛点是 ingress host 与插件边界没收住，不是消息会话模型缺失。
- 一次性设计 channel-agnostic 聊天会话模型会把范围扩大到 UI、审计、审批、身份、回执、幂等和存储结构。
- 可以先用 typed `notification.receive` + receive record 解决宿主边界，再在后续 issue 中评估是否需要更高层消息模型。

## API / Core / Plugin SDK / Plugin Responsibilities

### apps/api

应该暴露：

- 通用 notification ingress route / host
- 请求级 raw HTTP 数据读取
- request id、异常映射、公共响应壳

不应该暴露：

- 渠道专属业务配置体系作为长期平台真源
- 频道语义、slash command 语义、bot 协议语义
- 直接审批 / 直接执行 / 直接 publish

### packages/core

应该暴露：

- notification ingress orchestration
- notification receive record / audit boundary
- topic 发布 helper 或 orchestration 内的 event publish boundary
- 将 receive item 路由到 approval / reanalysis / other entrypoints 的平台级决策

不应该暴露给插件：

- DB session
- Event Bus publisher
- 审批 service 实现细节
- 任意 secret resolver

### packages/plugin-sdk

应该暴露：

- `NotificationSendInput/Result`
- 新的 `NotificationReceiveInput`
- 现有 `NotificationReceiveItem/Result`
- JSON-safe DTO 校验与结构化错误

不应该暴露：

- FastAPI request/response
- host framework object
- runtime service locator

### plugins/notifications/*

应该暴露：

- manifest
- config schema
- send / receive capability implementation
- 渠道专属协议适配

不应该承担：

- 业务主链状态流转
- 事件发布
- 平台审计与持久化真源

## Risks / Trade-offs

- [Risk] 为 `notification.receive` 增加 typed input 后，现有 Discord 插件和测试需要迁移。
  -> Mitigation：保留一段最小兼容层，由 runtime orchestration 或 adapter 把旧 mapping 迁移到新 DTO。

- [Risk] 引入 `notification.received` topic 会扩大 Event Bus topic 集合。
  -> Mitigation：在 spec 中显式登记，并限制只有平台 orchestration 能发布，避免 topic 泛滥。

- [Risk] API 层从 Discord 专属 service 收敛到通用 ingress host，会触碰当前路由、settings、测试和 README。
  -> Mitigation：第一版保留现有公开 route 形状，只先改内部编排边界，减少外部兼容成本。

- [Risk] 过早设计过宽的 channel-agnostic 模型会拉大范围。
  -> Mitigation：本 change 只收住 ingress host、typed receive contract、orchestration 和 Discord 样板，不引入完整 chat/session 领域。

## Migration Direction

1. 新建 Notification Plugin Ingress V1 change，先形成 OpenSpec-only PR。
2. 维护者认可后，再进入实现。
3. 实现阶段先补 `plugin-sdk` 的 `notification.receive` typed input。
4. 再补 core 层 notification ingress orchestration。
5. 最后以 Discord 插件为样板完成 API ingress 合规改造与测试迁移。

## Open Questions

- `notification.received` 是否作为稳定 topic 进入 Event Bus V1 默认集合，还是先只作为 core 内部编排记录，后续再公开？
- receive item 的平台持久化对象应命名为 `NotificationReceiveRecord`、`NotificationIngressRecord`，还是直接作为未来 `ApprovalInput` 的来源对象之一？
- 通用 ingress host 是否需要支持一个 route 对应多个 plugin binding，还是第一版只支持“一条 route 绑定一个 notification plugin”？
