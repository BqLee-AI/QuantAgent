## 1. OpenSpec 评审

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `model-provider-multi-provider-v1` 的 proposal、design、spec、tasks 和必要元数据。
- [ ] 1.2 在 PR 说明中链接当前需求和 `model-provider-config-minimal-v1`，写清本 PR 只重规划多 provider 配置、固定任务模型预设、基础 fallback 和基础默认模型，不进入完整 ProviderPolicy / budget / routing 平台。
- [ ] 1.3 运行 `openspec validate model-provider-multi-provider-v1 --type change --strict --json`。
- [ ] 1.4 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. 迁移与核心建模

- [x] 2.1 设计并实现 `model_providers` 数据模型，替换当前单条 `model_configs` 结构，字段覆盖 id、name、provider_type、base_url、enabled、is_default、encrypted_api_key、last_error、created_at、updated_at。
- [x] 2.2 为 provider 下模型增加独立数据模型，至少覆盖 model_name、enabled、supports_vision、is_global_default、timestamps。
- [x] 2.3 为系统固定任务类别增加 preset 绑定模型，类别在代码层写死：`global_default`、`economy_text`、`general_text`、`reasoning_text`、`multimodal`。
- [x] 2.4 为 invocation log 增加 `provider_id` 和可选 `preset_key` 关联字段，并设计旧记录兼容策略。
- [x] 2.5 新增 repository / storage 边界，承接 provider 列表、详情、默认项唯一约束、preset 查询、fallback 解析和迁移兼容逻辑。
- [x] 2.6 设计 migration：把旧单条 global config 转成一条 provider 记录；若存在旧 model 字段，则同步迁移成 provider 下一条模型记录并绑定为 `global_default`。
- [x] 2.7 保持加密工具复用，测试 key 加密、解密、默认 provider 不变量和全局默认模型不变量。

## 3. Core service / adapter

- [x] 3.1 将 `ModelConfigService` 重构为多 provider service，支持 provider list / get / create / update / set-default / test-connection / list-invocations。
- [x] 3.2 增加 provider 模型 CRUD、全局默认模型设置和固定任务 preset 绑定能力。
- [x] 3.3 实现最基础 fallback 解析：类别主模型 -> 类别 fallback 模型（可选） -> 全局默认模型（能力兼容时）。
- [x] 3.4 将固定 smoke 调用继续保留在 provider client port 后，按 provider id 记录 invocation，并在适用时写入 `preset_key`。
- [x] 3.5 为默认 provider 选择、禁用默认 provider、缺 key、preset 未绑定、fallback 不可用、并发 default 切换等失败路径补充 service 逻辑和短注释。

## 4. API / Contracts

- [x] 4.1 用 `providers` 资源语义替换当前单对象 `/models/config` 接口，定义 list/detail/create/update/set-default/test-connection DTO。
- [x] 4.2 增加 provider 下模型 CRUD DTO 和固定任务 preset 查询 / 更新 DTO。
- [x] 4.3 更新 `/api/v1/models/invocations` 支持 `provider_id` 与 `preset_key` 过滤和关联字段。
- [x] 4.4 更新 `packages/contracts/schemas/`，覆盖 provider summary、provider detail、provider model、global default model、preset binding 和 invocation relation。
- [x] 4.5 为新接口补齐 API 测试和 OpenAPI 契约测试，确保 key 永不明文回显。

## 5. Web `/models` 重构

- [x] 5.1 将当前单 provider `/models` 页面重构为两个主要视图：`供应商配置` 和 `任务模型预设`。
- [x] 5.2 在 `供应商配置` 视图中实现 provider 列表 + provider 详情 + 状态/usage 面板。
- [x] 5.3 在 provider 详情中支持 provider 下模型管理、全局默认模型选择和测试连接。
- [x] 5.4 在 `任务模型预设` 视图中展示固定类别卡片或面板：`global_default`、`economy_text`、`general_text`、`reasoning_text`、`multimodal`。
- [x] 5.5 为每个固定类别支持主模型绑定、fallback 模型绑定和能力 / 缺失校验状态。
- [x] 5.6 新增 `features/models/components/ProviderListPanel.tsx`、`ProviderEditorForm.tsx`、`ProviderStatusPanel.tsx`、`ModelPresetBoard.tsx` 或等价拆分，不把列表、详情、状态、preset、请求逻辑堆进一个文件。
- [x] 5.7 用 HeroUI 构建列表、表单、默认项按钮、启停开关、测试连接按钮和状态标记，样式优先 Tailwind。
- [x] 5.8 补齐 loading / empty / error / permission denied / sensitive masked / preset validation 状态。
- [ ] 5.9 为新增 provider 提供模板化入口，至少覆盖 OpenAI、Anthropic、DeepSeek、Qwen、Moonshot、OpenRouter 和自定义 OpenAI-compatible。
- [ ] 5.10 为 provider 列表补齐关键字搜索和基础状态筛选：全部 / 已启用 / 默认 / 异常 / 缺少 Key。

## 6. 验证

- [x] 6.1 `openspec validate model-provider-multi-provider-v1 --type change --strict --json`
- [x] 6.2 `uv run python -m unittest discover -s packages/core/tests`
- [x] 6.3 `cd apps/api && uv run python -m unittest discover -s src/tests`
- [x] 6.4 `bun run --cwd apps/web test:unit`
- [x] 6.5 `bun run --cwd apps/web build`
- [x] 6.6 `bun run --cwd apps/web lint`
- [x] 6.7 使用 mock provider 验证多 provider 列表、默认项切换、固定任务模型预设绑定、基础 fallback 和 provider / preset 维度 invocation 记录。

## 7. 明确后续不混入本轮

- [ ] 7.1 `fast` / `balanced` / `reasoning` / `local` 这类用户可编辑 ProviderPolicy 另开 change。
- [ ] 7.2 fallback chain 可视化编辑、budget、cost governance、auto discovery、LiteLLM Proxy 另开 change。
- [ ] 7.3 原生 Anthropic / Gemini 协议适配、AgentDefinition 绑定 policy、模型评估平台不进入本轮。
