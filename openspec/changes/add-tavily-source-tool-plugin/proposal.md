## Why

QuantAgent 已经通过 `official-plugin-v1-main-chain` 收住了官方插件主链路边界，并明确 Tavily 在该链路中的定位是 evidence source/data tool：它负责对外提供搜索和链接正文抽取能力，供后续其他插件、Agent 或 ToolRegistry 通过受控工具边界调用，而不是自己承担插件编排、事件链路或运行时职责。

当前仓库虽然已经有 `readability-source` 这类单链接正文读取插件，但还缺少一个主动检索外部证据的官方能力。仅靠 RSS 或已知 URL reader，无法支持“先检索相关外部资料，再对候选链接做高质量抽取”的链路。若这层能力继续缺失，后续 analysis、strategy、crawler 或行业插件实现时就会被迫把搜索、抽取、第三方 API 适配、schema 契约和运行时边界一起混做，导致 scope 漂移，也容易把 Tavily 误做成“插件互调入口”。

这一刀先只收住官方 `Tavily` Source/Data Tool Plugin 的插件包边界、配置契约、`search` / `extract` 输入输出 schema、适配器落位和测试策略，让它成为后续证据链路可复用的受控工具插件。

## What Changes

- 定义官方 `Tavily` Source/Data Tool Plugin 的最小插件包边界和目录结构。
- 定义 `plugin.yaml`、`config.schema.json`、README、入口实现、最小 fixture/mock 测试和工具 schema 交付要求。
- 定义第一版只暴露 `search` 与 `extract` 两类 capability，对应官方工具 ID 和 schema 化输入输出。
- 定义 Tavily client adapter 边界，隔离第三方 SDK / HTTP API 细节，不把第三方请求逻辑散落进插件入口。
- 明确插件只消费平台传入的校验后配置 DTO / `effective_config`，不负责配置保存、secret 管理、Runtime、ToolRegistry、事件入库、审计或调度。
- 明确本轮接入方式采用“Runtime 协议优先、可选复用 `BasePlugin`”的策略，以兼容当前 runtime 最佳实践并避免不必要的继承耦合。

## Capabilities

### New Capabilities

- `tavily-source-tool-plugin`: 官方 `Tavily` Source/Data Tool Plugin 对外暴露 `search` 与 `extract` 两类受控工具能力，返回统一 JSON DTO，供后续 Plugin Runtime / ToolRegistry / 其他插件链路调用。

## Impact

- `plugins/sources/tavily-source/`
- `packages/plugin-sdk/` 现有 runtime / DTO 契约的复用方式
- `docs/design/06-source-plugin-design.md`
- `openspec/changes/official-plugin-v1-main-chain/`
- 可能新增 Tavily 官方 Python SDK 或等价 HTTP client 依赖，但该依赖只属于插件目录实现细节，不应改变 core / API / web 的依赖方向
