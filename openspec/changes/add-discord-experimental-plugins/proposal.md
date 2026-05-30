## Why

Issue #110 需要在不改动核心 Runtime / 审批边界的前提下，补齐第一版官方 Discord 实验性收发能力。当前仓库已经有可运行的发送与接收样板，但它们被拆成两个官方插件，和本轮会议收敛出的“尽量完善为一个 Discord 插件”方向冲突。如果不先统一真源，后续 reviewer、实现和测试会继续在“两插件”与“单插件”之间分叉。

## What Changes

- 将第一版 Discord 官方实验能力从“发送插件 + 接收插件”收敛为“一个官方 Discord 插件”。
- 该插件仍通过单个 `plugin.yaml` 和单个 `config.schema.json` 进入 Registry，并在同一插件边界内承接发送与接收两类低风险能力。
- 插件目录、README、standalone smoke/test 和配置契约统一收敛到一个官方插件目录下。
- API ingress 与 Registry 校验不再依赖“Discord 接收必须是 `source` 类型插件”的旧假设，而改为校验受支持 capability 与插件处理器。
- 保持主要业务代码仍尽量落在 `plugins/` 内；如果必须动 API 或 core，只允许做最小兼容性收口，不扩展新的 plugin type 或通用 webhook 框架。

## Capabilities

### Modified Capabilities

- `discord-experimental-plugins`: 定义 QuantAgent 第一版官方 Discord 实验插件从双插件拆分收敛为单插件的边界、配置、安全约束和独立验收要求。
- `plugin-registry-v1`: 补充单个官方 Discord 插件作为 Registry V1 样板能力，但不新增第二套 manifest、第二套 schema 或新的核心注册机制。

## Impact

- `plugins/notifications/**`：第一版官方 Discord 插件统一落在官方 notification 插件目录下。
- `apps/api/src/quantagent/api/services/discord_interactions.py` 与相关测试：收敛旧的 source-type 假设。
- `packages/core/tests/test_registry.py` 与相关测试：更新官方 Discord 插件扫描期望。
- `openspec/changes/enable-real-discord-interaction-webhook/**`：同步对齐真实 ingress 对单插件的调用边界。
