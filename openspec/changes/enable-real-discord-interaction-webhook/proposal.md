## Why

当前仓库的真实 Discord interaction ingress 已经打通，但它建立在“接收侧是独立 source plugin”这个前提上。会议结论要求把 Discord 收发尽量收敛为一个插件，因此这条 ingress change 也必须同步改口径，否则 API 配置、type 校验和测试仍会强迫 Discord 接收回到双插件模式。

## What Changes

- 让真实 Discord interaction ingress 对接单个官方 Discord 插件，而不是独立的 source plugin。
- 保持官方 `Ed25519` 验签、`PING`、最小 `APPLICATION_COMMAND` 首响和 plugin entrypoint loader 边界不变。
- 将 API ingress 的合法性判断从“必须是 source type”收敛为“必须是可加载的 Discord 插件，并暴露接收 handler / capability”。
- 同步更新文档、默认配置、测试和 smoke 验证口径。

## Capabilities

### Modified Capabilities

- `discord-interaction-webhook-ingress`: 定义真实 Discord interaction webhook 对单个官方 Discord 插件的 API ingress、官方验签、最小响应和插件调用边界。

## Impact

- `apps/api/src/quantagent/api/routers/v1/`：保留公开 ingress 路由，但更新目标 plugin 假设。
- `apps/api/src/quantagent/api/config/`：更新默认 Discord plugin id。
- `plugins/notifications/**`：真实接收能力的 entrypoint 与 README 收敛到单插件目录。
- `packages/core/`：最小 entrypoint loader 复用现状，不新增新的 runtime 协议。
