## Why

QuantAgent 后续 AgentRuntime、RouterAgent 和行业 Agent 都依赖可用的模型调用能力，但当前仓库还没有一个可由前端配置、由后端读取并可统计 token usage 的最小模型配置闭环。

本 change 先收住 issue #156 的最小可运行目标：配置一个全局 OpenAI-compatible 模型供应商、加密保存 API key、完成固定 smoke 调用并记录基础 token usage。它不进入完整 ProviderPolicy、fallback、budget 或模型治理平台，避免在系统还未跑通前把范围拉大。

## What Changes

- 定义单个全局模型配置的 V1 行为：provider 类型固定为 `openai_compatible`，配置项包含显示名称、base URL、model、enabled 和 API key。
- 定义 API key 入库边界：写入请求可提交明文 key，后端必须用 Fernet 类对称加密保存；查询、日志、错误响应和前端页面不得回显明文 key。
- 定义最小模型配置 API：查询配置、保存配置、执行固定 smoke 测试连接、查询最近模型调用与 token usage。
- 定义独立 model invocation log：记录 provider、model、prompt tokens、completion tokens、total tokens、status、错误摘要、request_id 和可选 `agent_run_id`。
- 定义前端 `/models` 最小入口：配置表单、masked key 状态、保存状态、测试连接状态、最近错误和基础 token 统计。
- 明确本 change 不实现 ProviderPolicy、`fast/balanced/reasoning/local`、fallback、budget、cost governance、自动模型发现、LiteLLM Proxy、prompt 编辑器或 AgentDefinition 编辑器。

## Capabilities

### New Capabilities

- `model-provider-config-minimal-v1`: 覆盖最小模型供应商配置、API key 加密入库、固定 smoke 测试连接、模型调用 token usage 记录和前端 `/models` 最小管理入口。

### Modified Capabilities

- 无。

## Impact

- `packages/core`: 后续实现全局模型配置、API key 加密、模型调用适配和 invocation log 的核心边界。
- `apps/api`: 后续暴露 `/api/v1/models/**` 管理 API，保持 DTO、鉴权、envelope 和错误映射的薄边界。
- `apps/web`: 后续新增或补齐 `/models` 页面，提供配置、测试连接和 token usage 展示。
- `packages/contracts`: 后续承载跨前后端模型配置与 invocation DTO / schema 生成边界。
- 后续实现 PR 可能新增 `cryptography` 后端依赖；本 OpenSpec-only change 不添加依赖或实现代码。
