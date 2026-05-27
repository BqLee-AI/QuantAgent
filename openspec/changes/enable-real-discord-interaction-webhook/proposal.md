## Why

当前仓库的 Discord 接收插件只支持插件内 HMAC fixture 和本地 standalone 验证，不能直接作为 Discord Developer Portal 的真实 Interactions Endpoint 使用。用户已经明确要求“真正实现接收功能，而不是只能本地测试”，因此需要新增一个 change，把真实 Discord webhook ingress、官方签名校验和最小交互响应边界正式收敛出来，避免实现时继续靠硬编码或口头约定推进。

## What Changes

- 新增一个面向真实 Discord Interactions Endpoint 的 API ingress 路径，允许 Discord 通过 HTTP `POST` 直接回调 QuantAgent。
- 将现有 Discord source 插件的验签逻辑从实验性 HMAC fixture 升级为 Discord 官方 `Ed25519` 请求签名校验，并支持 Discord `PING` 握手。
- 为真实接收路径定义最小可运行响应策略：对合法 `PING` 返回 `PONG`，对受支持的 interaction 返回合法 Discord interaction response，而不是仅返回插件内 DTO。
- 增加一个最小插件 entrypoint 加载路径，使 API ingress 能根据 Registry 中的 `plugin.yaml` 定位并调用 source plugin，而不是在核心代码里硬编码 Discord 插件 import。
- 补充 API、插件和验证文档，明确环境变量、Developer Portal 配置方式、真实 smoke test 和非目标边界。

## Capabilities

### New Capabilities
- `discord-interaction-webhook-ingress`: 定义真实 Discord interaction webhook 的 API ingress、官方验签、最小响应和插件调用边界。

### Modified Capabilities

## Impact

- `apps/api/src/quantagent/api/routers/v1/`: 新增或扩展 Discord interaction webhook 的公开路由。
- `apps/api/src/quantagent/api/config/`: 新增 ingress 所需环境变量和配置读取。
- `apps/api/src/tests/`: 新增 Discord interaction webhook 路由与 OpenAPI/行为测试。
- `plugins/sources/discord-interaction-webhook/`: 将插件从 HMAC fixture 接收器升级为真实 Discord interaction 处理器。
- `packages/core/`: 可能新增最小 plugin entrypoint loader，使 API 能通过 manifest 调用 source plugin。
- Discord Developer Portal 配置、真实公网回调地址和本地 smoke 验证流程。
