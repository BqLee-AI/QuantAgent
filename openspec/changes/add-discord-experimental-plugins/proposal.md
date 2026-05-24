## Why

Issue #110 需要在不改动核心 Runtime / API / 审批边界的前提下，补齐第一版官方 Discord 实验性收发能力。当前仓库只有插件注册骨架和 source 占位插件，没有可运行、可独立测试的 Discord 官方插件样板，继续直接实现代码会让插件边界、接收方式和验收口径停留在对话里。

## What Changes

- 新增一个 OpenSpec change，定义第一版 Discord 官方实验性插件组的边界：发送走 `notification` 插件，接收走 `source` 插件。
- 明确接收路径固定为 `Webhook Push`，并要求第一版标准化终点停在插件内 DTO，不接入核心 Event Bus、审批回流或统一聊天通道。
- 要求两个插件都通过 `plugin.yaml` 注册，配置使用 secret reference，主要代码改动控制在 `plugins/` 范围内。
- 为发送和接收分别定义独立 mock / fixture / standalone test harness 与结构化错误边界。
- 要求 README 明确实验范围、支持能力、敏感配置和非目标，避免实现中顺带扩展核心契约。

## Capabilities

### New Capabilities
- `discord-experimental-plugins`: 定义 QuantAgent 第一版官方 Discord 实验性发送与接收插件的边界、配置、安全约束和独立验收要求。

### Modified Capabilities
- `plugin-registry-v1`: 补充官方 Discord 实验插件作为通过 `plugin.yaml` 注册进入 Registry 的新样板能力，但不改变 Registry V1 的既有要求。

## Impact

- `plugins/notifications/**` 与 `plugins/sources/**`：后续落位官方 Discord 发送与接收插件。
- `packages/core/tests/test_registry.py` 或等价 Python 测试入口：后续验证新插件 manifest / schema 可被 Registry 扫描。
- `docs/design/03-plugin-system-and-registry.md` 与 `docs/design/06-source-plugin-design.md`：本 change 复用其边界，但不在本轮改动核心设计或运行时协议。
- OpenSpec-only 审核通过前，不进入实现代码、依赖升级、API 路由或核心 runtime 改动。
