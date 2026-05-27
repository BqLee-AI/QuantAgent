## Context

当前 Discord source 插件只做到“插件内接收和解析”，README 也明确说明还不支持真实 Discord interaction webhook 端到端联调。要把它变成真实可用能力，不只是把 HMAC 换成 `Ed25519`，还必须同时补齐三类缺口：

- Discord 官方要求的 HTTP 请求头校验和 `PING` 握手。
- 一个可以挂到 Discord Developer Portal 的稳定 HTTP ingress。
- 一个不依赖硬编码 import 的最小插件加载路径，让 API 层仍然通过 `plugin.yaml` 和 Registry 边界调用 source plugin。

官方文档当前要求：Discord 通过 `X-Signature-Ed25519` 和 `X-Signature-Timestamp` 发送签名，请求失败时应返回 `401`；配置 Interactions Endpoint URL 时，Discord 会先发送 `type: 1` 的 `PING`，服务端需要返回 `200` 和 `{"type":1}`。对正常 interaction，请求必须在 3 秒内给出首个响应。以上要求来自 Discord 官方文档《Interactions Overview》和《Receiving and Responding to Interactions》。

## Goals / Non-Goals

**Goals:**

- 提供一个真实可配置的 Discord Interactions HTTP ingress，让 Discord Developer Portal 能成功验证并发送请求。
- 让现有官方 Discord source plugin 支持官方 `Ed25519` 签名校验，而不是仅支持 HMAC fixture。
- 保持插件注册边界不变：API 层通过 Registry record + manifest entrypoint 定位插件，不在核心代码里写死 Discord class/import。
- 为合法 `PING` 和最小支持的 interaction type 返回 Discord 可接受的响应格式。
- 为这条真实接收路径补齐最小测试、README 和 smoke 验证说明。

**Non-Goals:**

- 不在本轮把接收结果接入 Event Bus、`RawEvent`、审批回流、自动执行或统一聊天通道。
- 不在本轮支持 gateway、bot polling、message component、autocomplete、modal submit 或 followup message 全链路。
- 不引入完整 plugin runtime、动态热重载或任意插件 HTTP 路由系统；只补真实 Discord webhook 所需的最小加载能力。
- 不在本轮实现公网部署、反向代理或隧道服务自动化。

## Decisions

### 1. 使用公开 API v1 路由承接 Discord 回调

真实 Discord interaction ingress 将落在 `apps/api`，作为公开 `POST` 路由由 `register_api_v1_routes` 统一注册。路由本身只负责：

- 读取原始 body 和 Discord 签名头。
- 读取 API 层配置。
- 通过 Registry + loader 获取目标 source plugin。
- 调用插件并把结果映射成 HTTP 响应。

这样符合 `apps/api` 的传输层职责，也避免在插件目录内自行启动 HTTP server。替代方案是让插件目录自己跑一个独立 webhook server，但这会绕过现有 API 边界和 Request ID / 异常处理链，因此不采用。

### 2. 入口路径固定为单一 Discord interaction endpoint

本轮使用单一公开 endpoint，例如 `/api/v1/integrations/discord/interactions`。它不暴露“任意 plugin id 路径参数”，也不直接作为通用 webhook ingress。原因是当前仓库没有通用 push source ingress 规范，若直接抽象成通用 webhook 框架，范围会快速扩展到更多 source 类型。

替代方案是直接设计 `/api/v1/webhooks/{provider}/{binding_id}` 这类通用入口，但这会提前引入 SourceBinding、路由分发和更多长期契约，因此不采用。

### 3. 插件调用必须走 manifest entrypoint，而不是硬编码 Discord import

当前 `packages/core` 只有 Registry 扫描，没有运行时加载 entrypoint 的能力。为满足“插件只能通过 `plugin.yaml` 和 Registry 进入系统”的仓库约束，本轮新增一个最小 loader：

- 输入：一个 `PluginRecord`。
- 行为：解析 `manifest.entrypoint`，以插件目录为模块搜索根导入目标模块，再读取导出的 `plugin` 对象。
- 限制：只允许加载 `VALID` 状态记录，且只服务于这条 ingress 路径。

替代方案是 API 路由直接 `import plugins.sources.discord-interaction-webhook...`。这虽然实现更快，但违反仓库关于插件注册和硬编码 import 的长期规则，因此不采用。

### 4. 接收插件升级为官方验签 + 真实 interaction 结果

现有插件 `receive_request(...)` 返回 `ReceiveResult` 和 DTO，但真实 Discord endpoint 还需要一个可直接映射到 HTTP 响应的结果结构。本轮将插件升级为：

- 使用 `X-Signature-Ed25519` 和 `X-Signature-Timestamp` 校验原始 body。
- 接受 Developer Portal 提供的 application public key 作为配置引用值。
- 识别 `PING` (`type=1`) 并返回 `PONG` 响应意图。
- 对支持的 `APPLICATION_COMMAND` (`type=2`) 继续产出标准化 DTO，同时返回一个最小 interaction response 意图。

这里不继续沿用 HMAC fixture 作为生产行为，但测试中仍可保留 fixture 或新增真实签名测试向量。替代方案是把官方验签写死在 API 路由，再把插件只当纯 parser。这个方案会让 source plugin 丢失接收和鉴权职责，因此不采用。

### 5. 首版命令响应使用立即返回的最小文本消息

对成功处理的 `APPLICATION_COMMAND`，本轮返回一个合法的最小 interaction response，而不是 `DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE`。原因是 deferred 路径需要后续 callback 或 followup message 设施，而当前仓库没有对应能力。

因此首版采用立即返回消息的策略，例如 `type=4` 并附带一条最小文本确认消息；如需要限制频道噪音，可以把消息设置为 ephemeral。Discord 官方文档当前允许在 interaction response data 中使用 `flags: 64` 发送仅用户可见的 ephemeral 消息。

替代方案是返回 `type=5` 延迟响应。但在当前没有 followup/edit-original 基础设施的前提下，这只会留下半成品，因此不采用。

### 6. 配置通过 API 环境变量 + 插件 config 双层收敛

真实 ingress 需要至少两类配置：

- API 层：是否启用 endpoint、目标 plugin id、Discord public key 引用或值。
- 插件层：allowlist、最小响应文案、timestamp tolerance 等行为配置。

API 层配置来自环境变量，避免硬编码真实值；插件层继续通过 `config.schema.json` 描述可审计字段。由于 Discord public key 不是敏感 secret，但仍不应写死到源码或样例中，因此可继续通过“reference + env 提供映射值”的形式传递给插件。

## Risks / Trade-offs

- [Risk] 只为 Discord ingress 引入最小 loader，后续可能与更完整 plugin runtime 方案重复。
  -> Mitigation：把 loader 明确限制为“最小 entrypoint 解析能力”，不提前设计动态生命周期和通用运行时。

- [Risk] 当前 source 设计文档强调 push source 最终应进入 `RawEvent` / Event Bus，本轮仍停在插件内 DTO + 最小响应。
  -> Mitigation：在 spec 和 README 中明确这是“真实 ingress 第一刀”，不等同于系统级 push source 全链路落地。

- [Risk] 公开 webhook endpoint 会引入噪音探测、重放和日志脱敏压力。
  -> Mitigation：严格校验签名和 timestamp，失败统一返回 `401` 或结构化错误，不记录完整原始 body 或公钥原文。

- [Risk] Discord 文档后续可能扩展 interaction 类型或响应约束。
  -> Mitigation：首版只承诺 `PING` 和最小 `APPLICATION_COMMAND`；其他类型显式返回不支持，后续再按官方文档增量扩展。

## Migration Plan

1. 先提交 OpenSpec-only PR，确认 endpoint 路径、最小响应策略和 loader 边界。
2. 实现 API 路由、配置、loader 和插件升级。
3. 在本地或测试环境暴露一个可被 Discord Developer Portal 访问的 HTTPS 地址。
4. 在 Developer Portal 配置 Interactions Endpoint URL，验证 `PING` 成功。
5. 再执行最小 slash command 或等价 interaction smoke test。
6. 若回滚，移除 endpoint 配置并撤销 Developer Portal URL；保留旧的 standalone fixture 测试。

## Open Questions

- 首版成功响应文案是否统一使用固定确认文本，还是允许通过插件配置覆盖。
- 首版是否只支持 `APPLICATION_COMMAND`，还是同时接受 `MESSAGE_COMPONENT` 并返回明确不支持结果。
- API 层保存公钥值时使用独立环境变量，还是复用未来统一 secret/provider 抽象。
