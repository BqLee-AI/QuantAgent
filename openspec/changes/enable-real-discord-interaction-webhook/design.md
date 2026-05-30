## Context

当前 Discord 真实 ingress 已经具备：

- Discord 官方 `Ed25519` 请求签名校验
- `PING` 握手
- 最小 `APPLICATION_COMMAND` 响应
- 通过 Registry + entrypoint loader 调用插件

但它把目标插件硬限定为独立 `source` 类型插件，而本轮会议结论要求 Discord 收发尽量收敛成一个插件。由于单插件方案不会顺手扩展新的 plugin type，本 change 需要把 ingress 的调用条件从“source plugin”改成“单个 Discord 插件的接收能力”，同时保持 API、loader 和失败边界最小稳定。

## Goals / Non-Goals

**Goals:**

- 让真实 Discord interaction ingress 对接单个官方 Discord 插件。
- 保持官方验签、`PING`、最小 command 首响和 plugin loader 边界不变。
- 用 capability/handler 校验代替 source-type 硬限制。
- 更新文档、默认 plugin id 和测试期望，使其与单插件方案一致。

**Non-Goals:**

- 不引入通用 webhook ingress 框架。
- 不把接收结果接入 Event Bus、`RawEvent`、审批回流、自动执行或统一聊天通道。
- 不扩展新的 plugin type 或多 manifest/plugin bundle 模型。
- 不支持 gateway、polling、message component、autocomplete、modal submit 或 followup message 全链路。

## Decisions

### 1. 公开 API ingress 路由保持不变

真实 Discord interaction ingress 仍然落在 `apps/api` 的公开 `POST` 路由，由 `register_api_v1_routes` 统一注册。HTTP 边界、异常映射和 Request ID 链路保持现状，不把 webhook server 下沉到插件目录。

### 2. API ingress 不再要求目标插件是 `source` type

本轮 SHALL 移除“Discord interaction ingress 只能加载 `PluginType.SOURCE` record”的旧限制，改为检查：

- record 存在且 `VALID`
- entrypoint 可加载
- manifest capability 集合包含接收所需 capability
- 插件对象暴露 `receive_request(...)`

原因是单插件方案下，Discord 插件会沿用既有 `notification` 类型，但仍需承接低风险接收能力。

### 3. 单插件接收能力继续通过显式 handler 暴露

Discord 插件继续通过 `receive_request(config, headers, body)` 暴露接收处理器，API ingress 不负责验签与解析，只负责：

- 读取原始 body 和 Discord 签名头
- 读取 API 层配置
- 加载目标插件
- 调用插件并把结果映射成 HTTP 响应

这样能保持插件边界清楚，也避免 API 侧重回“硬编码 Discord 解析器”。

### 4. 默认 plugin id 与 README 需要同步收口

API 默认配置、README、测试和 smoke 文档 SHALL 使用新的单插件官方 plugin id，不再引用旧的 source 插件 id。

### 5. 失败边界保持不变

以下失败语义保持现状：

- 签名、时间戳错误 -> `401` / 未授权结果
- 不支持的 interaction type -> 明确 `400`
- plugin id 不存在、record 非法、entrypoint 无法加载、handler 缺失 -> `503` / 服务不可用

新增的非显然点是：plugin 合法性不再由 `type == source` 代理，而由 capability 与 handler 共同约束。

## Directory / File Planning

受影响文件：

- `apps/api/src/quantagent/api/services/discord_interactions.py`
  负责 API 私有编排与单插件合法性校验
- `apps/api/src/tests/test_app.py`
  更新旧 plugin id / type 的测试假设
- `apps/api/src/quantagent/api/config/settings.py`
  更新默认 Discord plugin id
- `apps/api/README.md`
  更新真实接收配置示例
- 单插件目录下的 README / smoke 文档

## Risks / Trade-offs

- [Risk] API ingress 改为 capability/handler 校验后，未来其他插件可能想复用这条例外路径。
  -> Mitigation：在代码注释和 spec 中明确，这只是 Discord 单插件的定向兼容，不是通用 webhook runtime。

- [Risk] 单插件默认挂在 `notification` 类型下，会让“接收能力”的可发现性变弱。
  -> Mitigation：通过 manifest capability 和 README 清楚声明接收能力，并在 API 配置与测试中显式引用。
