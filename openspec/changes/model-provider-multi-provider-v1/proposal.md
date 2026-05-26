## Why

当前 `model-provider-config-minimal-v1` 只支持一条全局 `openai_compatible` 配置，能跑通最小链路，但产品形态过于简陋：用户无法像大多数 AI 软件那样维护多个模型供应商、切换默认 provider、保留多套 key/endpoint/model 组合，也无法在页面上直接理解“当前系统有哪些 provider、哪个在启用、哪个失败、哪个缺 key”。

`docs/prd/pages/12-models.md` 已经把 `/models` 定位为模型治理入口。只做“多 provider 配置管理”仍然不够，因为产品内存在多种任务场景：轻量摘要/筛选、通用文本任务、复杂推理任务和多模态任务，对模型能力和成本的要求不同。用户不应该自己定义这些任务类别，但必须能够为系统内置类别选择默认模型。

因此本轮要把 `/models` 升级为一个真正可用的控制面：既能管理多个 provider，也能管理系统固定任务模型预设，并提供最基础的 fallback 和全局默认模型选择。后续完整 ProviderPolicy / budget / routing 平台仍然另开 change。

## What Changes

- 将单条全局模型配置升级为多 provider 列表管理：支持新增、编辑、启停、删除（软删除或禁用优先）和设置默认 provider。
- V1 仍聚焦 `openai_compatible` 类型，但配置对象改为“多条 provider 记录”，覆盖 OpenAI、兼容网关、vLLM、Ollama 兼容接口等常见接入方式。
- API key 继续入库并加密保存；查询、列表、日志和错误响应仍不得回显明文 key。
- 模型调用真源继续使用独立 invocation log，但每条记录要关联具体 provider 配置 id / name，支持默认 provider 与最近 usage 展示。
- 为系统内置的固定任务类别提供模型预设能力，类别先在代码中写死，不允许用户创建、删除或改名。V1 内置：
  - `global_default`
  - `economy_text`
  - `general_text`
  - `reasoning_text`
  - `multimodal`
- 每个固定类别支持选择主模型，且支持最基础的 fallback：类别主模型 -> 类别 fallback 模型（可选） -> 全局默认模型（能力兼容时）。
- `/models` 页面升级为常见软件样式：provider 列表与详情编辑 + 固定任务模型预设视图，支持新增 provider、选择默认 provider、设置全局默认模型、配置分类预设、连接测试和查看最近调用。
- V1 必须提供预置 provider 模板，而不是只提供空白创建。至少包含：OpenAI、Anthropic、DeepSeek、Qwen、Moonshot、OpenRouter 和自定义 OpenAI-compatible。
- V1 的 provider 列表必须支持搜索和基础状态筛选，至少覆盖：全部 / 已启用 / 默认 / 异常 / 缺少 Key。
- 保持现有最小 smoke check：固定 prompt，不接收用户 prompt，不发送真实事件、策略或敏感上下文。

## Non-Goals

- 本轮不实现 `fast` / `balanced` / `reasoning` / `local` 这类可编辑 ProviderPolicy。
- 本轮只实现固定顺序的基础 fallback，不实现可视化 fallback 链路编辑、budget / cost governance、自动模型发现或 LiteLLM Proxy 部署。
- 不实现 AgentDefinition 编辑器、prompt 编辑器或完整模型使用分析平台。
- 不把模型 key 下放到普通 Settings、插件配置或前端 runtime config。

## Capabilities

### New Capabilities

- `model-provider-multi-provider-v1`: 多 provider 配置管理、默认 provider 选择、全局默认模型、固定任务类别模型预设、基础 fallback、加密 key 入库、固定 smoke 测试连接、provider/任务类别维度 invocation usage 和 `/models` 管理页。

### Superseded Capabilities

- `model-provider-config-minimal-v1` 作为单 provider 最小闭环方案，被本 change 在产品形态和数据模型上覆盖；实现时需要说明迁移和兼容策略。

## Impact

- `packages/core`: 需要把单条全局模型配置模型升级为多条 provider 记录，并引入默认 provider、全局默认模型、固定任务模型预设和基础 fallback 解析。
- `apps/api`: 需要把 `/api/v1/models/**` 从单对象接口升级为列表 + 详情 + 默认项 + preset + action 语义。
- `apps/web`: 需要把 `/models` 从单表单页升级为 provider 列表 + 详情配置 + 固定任务模型预设 + 状态/usage 的管理台页面。
- `packages/contracts`: 需要更新 provider DTO / schema，从单配置对象扩到 provider summary / detail / preset binding / default selection / invocation relation。
