## Context

当前仓库已经存在 `model-provider-config-minimal-v1` 的单 provider 实现：数据库只有一条 `model_configs` 记录，API 是单对象 `/models/config` 读写，Web 也是单表单页面。这与 `docs/prd/pages/12-models.md` 的长期产品方向不一致，也不足以支撑“像大多数软件那样管理多个 provider”的实际使用方式。

本 change 需要在不直接进入完整 ProviderPolicy 平台的前提下，把数据模型、API 和前端形态升级到一个真正可用的模型控制面。重点不再只是 provider 列表、默认 provider、启停、脱敏 key 管理和 provider 维度 smoke / usage，还要增加系统固定任务模型预设、最基础 fallback 和全局默认模型。

## Goals / Non-Goals

**Goals:**

- 支持多条 provider 配置记录，而不是单条全局配置。
- 支持默认 provider 选择，供后续 AgentRuntime 读取。
- 支持全局默认模型选择，作为系统兜底模型。
- 支持固定任务模型类别预设，类别在代码层固定，不允许用户编辑类别定义。
- 支持最基础 fallback：类别主模型失败或不可用时，按固定规则回退。
- 支持 provider 列表页、详情编辑、启停、测试连接和基础 usage 查看。
- 保持 key 加密入库、查询脱敏和 invocation log 记录边界。

**Non-Goals:**

- 不实现可编辑 ProviderPolicy、复杂 fallback chain editor、budget、cost governance、自动 discovery、LiteLLM Proxy。
- 不引入 Anthropic / Gemini 原生 payload 分支；本轮 provider type 仍固定为 `openai_compatible`，但允许多条记录。
- 不把 key 存进 Settings、插件配置或 runtime config。
- 不支持用户自定义任务类别；类别定义属于产品内置系统常量。

## Architecture / Boundaries

### Directory Blueprint

- `packages/core/src/quantagent/core/model_config/`
  - `models.py`: provider 状态、key 状态、invocation 状态、默认 provider 选择结果、固定任务模型类别、preset 绑定结果和 fallback 解析结果等领域类型。
  - `crypto.py`: 保持 Fernet 加密边界不变。
  - `orm.py`: 从单条 `model_configs` 升级为多条 `model_providers`；新增 provider 下模型配置表，以及系统固定任务模型 preset 绑定表；invocation log 关联 `provider_id` 和可选 `preset_key`。
  - `service.py`: 提供 provider 列表、详情、保存、新增、默认项切换、禁用、测试连接、invocation 查询、preset 绑定和 fallback 解析；外部 provider 调用仍通过 client port。
  - `repository.py`（建议新增）: 因为现在已经存在列表、详情、默认项、唯一约束、preset 查询、fallback 解析和 migration 兼容逻辑，持久化读写开始具备真实复用和复杂度，适合从 service 中拆出 repository。
- `packages/core/alembic/versions/`
  - 新增 migration：把旧单条 `model_configs` 迁移到新 `model_providers` 结构，并保留兼容数据迁移逻辑。
- `apps/api/src/quantagent/api/schemas/models.py`
  - 新增 provider summary、provider detail、provider model item、create/update request、default selection response、preset binding DTO、list response、test connection request/response DTO。
- `apps/api/src/quantagent/api/routers/v1/models.py`
  - 从单对象接口改为列表/详情/action/preset 语义。
- `packages/contracts/schemas/`
  - provider list item、provider detail、provider model item、default provider summary、preset binding、invocation relation JSON Schema。
- `apps/web/src/features/models/`
  - `api.ts`: provider list/detail/create/update/test/default/preset actions。
  - `queries.ts`: list/detail/default/preset/invocations query 与 mutation。
  - `components/`
    - `ProviderListPanel.tsx`
    - `ProviderEditorForm.tsx`
    - `ProviderStatusPanel.tsx`
    - `ProviderInvocationTable.tsx`
    - `ModelPresetBoard.tsx`
    - `ModelPresetCard.tsx`
    - `ModelsPage.tsx`
  - `state.ts`（如需要）: 当前选中 provider id、当前激活 tab、本地新建态等轻量 UI 状态。
- `apps/web/src/routes/_app/(workspace)/models/index.tsx`
  - 保持 route 入口，只挂 feature 页面。

### Backend Boundaries

API router 继续保持薄层，只负责：

- HTTP path / query / body 解析
- auth / CSRF / request id
- DTO <-> core mapper
- `ApiResponse` envelope
- safe error mapping

Core 负责：

- provider 配置生命周期
- provider 下模型配置生命周期
- 默认 provider 选择规则
- 全局默认模型解析
- 固定任务模型预设和 fallback 解析
- key 加密 / 解密
- smoke 测试连接
- invocation 持久化
- 列表 / 详情状态推导

Repository 本轮建议引入。原因：

- 已有真实持久化复杂度：列表查询、详情查询、默认项唯一性、preset 查询、fallback 解析、迁移兼容、invocation 关联。
- 后续 AgentRuntime / ProviderManager 会复用 provider 解析、模型解析和 preset 读取。
- 这已经超出“单实现简单 upsert”场景，继续把 SQLAlchemy 读写堆在 service 中会变成大文件。

### Frontend Boundaries

Web route 继续只做页面入口。页面结构拆成：

- provider 列表区：展示 provider name、default、enabled、missing_key、failed 等概览，支持选择、新增、搜索和状态筛选。
- provider 详情区：编辑当前选中 provider 的 name、base URL、API key、enabled，并管理该 provider 下的模型列表。
- 状态与 usage 区：展示当前选中 provider 的 status、最近错误、最近 invocation、token usage。
- 任务模型预设区：展示系统固定类别、当前绑定模型、fallback 模型和能力校验状态。

新增 provider 入口不能只有空白表单。前端需要提供：

- 模板化新增入口
- 空白自定义入口

V1 模板最少包含：

- OpenAI
- Anthropic
- DeepSeek
- Qwen
- Moonshot
- OpenRouter
- 自定义 OpenAI-compatible

模板只负责预填名称、base URL 和常见模型示例，不改变后端 `openai_compatible` 单 adapter 边界。

服务端状态通过 TanStack Query 管理，不在 route 中手写 `fetch` 或 envelope。UI 组件优先 HeroUI `Button`、`Input`、`Switch`、`Table`、`Tabs`、`Chip`。

## Core Model / API Fields

### Provider Record

- `id`: provider 配置主键。
- `provider_type`: 仍为 `openai_compatible`。
- `name`: provider 显示名称，用户可自定义。
- `base_url`: endpoint / gateway base URL。
- `enabled`: provider 是否可用。
- `is_default`: 是否为默认 provider；数据库层需保证同一时刻最多一条默认 provider。
- `encrypted_api_key`: 加密后的 key。
- `last_error`: 最近安全错误摘要。
- `created_at` / `updated_at`.

### Provider Model Record

- `id`: provider 内模型记录主键。
- `provider_id`: 所属 provider。
- `model_name`: 运行时模型名。
- `enabled`: 模型是否可选。
- `supports_vision`: 是否支持视觉输入；V1 至少需要这个能力标记。
- `is_global_default`: 是否为全局默认模型；数据库层需保证全局最多一条。
- `created_at` / `updated_at`.

### System Model Preset Record

- `preset_key`: 固定任务类别键，V1 写死：
  - `global_default`
  - `economy_text`
  - `general_text`
  - `reasoning_text`
  - `multimodal`
- `primary_model_id`: 主模型绑定。
- `fallback_model_id`: fallback 模型绑定，可选。
- `updated_at`

### Provider Summary DTO

- `id`
- `provider_type`
- `name`
- `enabled`
- `is_default`
- `status`
- `key_status`
- `masked_key`
- `last_error`
- `model_count`
- `updated_at`

### Provider Detail DTO

在 summary 基础上增加：

- `base_url`
- `models`
- 可选 `last_tested_at`（若本轮实现成本合理）

### System Model Preset DTO

- `preset_key`
- `title`
- `description`
- `primary_model`
- `fallback_model`
- `status`
- `validation_message`

### Invocation DTO

- `id`
- `provider_id`
- `provider_name`
- `provider_type`
- `model`
- `preset_key`
- `status`
- `token_usage`
- `error_summary`
- `request_id`
- `trace_id`
- `agent_run_id`
- `created_at`

## API Shape

建议替换单对象接口为：

- `GET /api/v1/models/providers`
  - 返回 provider summary 列表和默认 provider id。
- `POST /api/v1/models/providers`
  - 新增 provider。
- `GET /api/v1/models/providers/{provider_id}`
  - 返回 provider detail。
- `PUT /api/v1/models/providers/{provider_id}`
  - 更新 provider。
- `POST /api/v1/models/providers/{provider_id}/actions/set-default`
  - 设置默认 provider。
- `POST /api/v1/models/providers/{provider_id}/actions/test-connection`
  - 测试单个 provider。
- `POST /api/v1/models/providers/{provider_id}/models`
  - 为指定 provider 新增模型记录。
- `PUT /api/v1/models/providers/{provider_id}/models/{model_id}`
  - 更新指定 provider 模型记录。
- `DELETE /api/v1/models/providers/{provider_id}/models/{model_id}`
  - 删除指定 provider 模型记录。
- `GET /api/v1/models/presets`
  - 返回固定任务模型预设及当前绑定关系。
- `PUT /api/v1/models/presets/{preset_key}`
  - 更新某个固定任务类别的主模型和 fallback 模型绑定。
- `GET /api/v1/models/invocations`
  - 支持 `provider_id` 和 `preset_key` 过滤，默认返回最近全局记录。

不建议继续扩展 `/models/config`。原因：

- 该命名已隐含“单对象配置”，继续兼容会让 API 语义混乱。
- 多 provider + 多模型 + preset 后，列表/详情/action 资源边界更清晰。

## Data Flow

1. 页面进入 `/models`，先拉取 provider 列表和最近 invocation。
2. provider 列表支持关键字搜索和状态筛选，帮助用户快速定位默认项、异常项和缺 key 项。
3. 默认选中默认 provider；若没有默认 provider，则选中第一条可用 provider 或进入空态。
4. 用户点击 provider 列表项，拉取详情并填充详情表单；API key 字段保持空白写入式更新。
5. 用户新增 provider 时，优先从预置模板创建；也允许切换到空白自定义创建。
6. 用户保存 provider：
   - 新 provider：创建记录并返回 summary/detail。
   - 已有 provider：更新非 secret 字段，若传 `api_key` 则重新加密覆盖。
7. 用户在 provider 详情中管理 provider 下模型列表，并可指定全局默认模型。
8. 用户点击“设为默认 provider”：
   - API 调 core service
   - core/repository 保证唯一默认 provider
   - 列表和详情 query 失效刷新
9. 页面进入“任务模型预设”视图，读取固定 preset 列表。
10. 用户为某个 preset 选择主模型和 fallback 模型：
   - 候选项仅来自 enabled provider 下的 enabled 模型
   - `multimodal` 仅允许选择 `supports_vision=true` 的模型
   - 保存后返回结构化校验状态
11. 用户测试连接：
   - 针对当前 provider 执行固定 smoke prompt
   - invocation log 写入 `provider_id`
   - 可选写入 `preset_key=global_default`
   - 状态面板和 invocation 表刷新

## Migration / Compatibility

- 旧表 `model_configs` 当前只有一条全局记录。
- migration 需要把该记录迁移成 `model_providers` 中的一条 provider 记录，并标记为默认 provider。
- 若旧记录中已有单一 `model` 字段，需要同步迁移成该 provider 下的一条模型记录，并设为 `global_default`。
- invocation log 需要新增 `provider_id` nullable 列，旧记录可根据 provider name / model 尝试回填；回填失败时允许为空，但新记录必须写入。
- 新增 preset 绑定表时，迁移需要初始化固定类别；除 `global_default` 外，其余类别可为空，等待用户配置。
- API 兼容策略：
  - 本 change 实现后，旧 `/models/config` 接口可以直接废弃并同步更新前端，因为当前功能尚未稳定发布。
  - 若维护者要求短期兼容，可保留只读 shim，但默认设计不建议继续维护双接口。

## Failure Paths

- 没有 provider：页面空态，允许创建第一条 provider。
- provider 缺 key：列表显示 `missing_key`，测试连接按钮禁用或返回结构化错误。
- 多条 provider 都被禁用：默认 provider 不可调用，页面显示“无可用默认 provider”。
- 某个 preset 未绑定主模型：页面显示缺口，运行时不得把它静默当成成功配置。
- `multimodal` preset 绑定到不支持视觉的模型：保存时拦截并返回结构化校验错误。
- preset 主模型不可用但 fallback 可用：运行时按固定顺序降级到 fallback。
- preset 主模型和 fallback 都不可用：若全局默认模型能力兼容，则退到全局默认模型；否则返回结构化“无可用模型”错误。
- 默认 provider 被删除/禁用：service 需尝试自动降级到下一条 enabled provider，或将默认项置空并返回结构化状态。
- 设置默认 provider 时并发冲突：repository / transaction 保证唯一默认项。
- provider HTTP 错误、超时、invalid response：记录到 invocation 和 `last_error`，不泄露 payload / key。
- 缺 `MODEL_CONFIG_ENCRYPTION_KEY`：创建或更新带 key 的 provider 返回安全配置错误。

## Reuse / Abstraction Choices

- 复用现有加密工具 `ModelConfigCrypto`。
- 复用现有 request id / envelope / auth capability `secret.manage`。
- 复用现有 invocation log 概念，但扩大为 provider + preset 维度。
- 不在本轮引入可编辑 ProviderPolicy、LiteLLM Proxy 或多 provider type adapter 分支。
- 固定任务类别使用代码常量 / enum，而不是数据库可编辑字典，避免产品关键路由被用户自定义破坏。
- 新增 repository 是本轮主要结构变化，因为持久化复杂度已超过当前 service 可读性边界。

## Validation Strategy

- OpenSpec: validate 新 change。
- Core:
  - provider list/detail/create/update/default selection
  - provider model CRUD
  - global default model invariant
  - fixed preset binding and fallback resolution
  - key encryption at rest
  - single default invariant
  - migration compatibility from old single row
  - smoke test and invocation relation
- API:
  - provider list/detail/create/update/set-default/test-connection
  - provider model CRUD
  - preset get/update
  - no plaintext key in responses
  - request id and safe errors
  - OpenAPI tags/schema
- Web:
  - provider list rendering
  - default selection flow
  - detail form save and model management
  - fixed preset board and validation states
  - masked key display
  - test connection states
  - empty/error/loading states

## Risks / Trade-offs

- [Risk] 现在只支持多条 `openai_compatible` 记录，看起来像多 provider，但本质仍是单 adapter。
  -> Mitigation: 本轮先收“多配置管理”问题；真正多 provider protocol 差异另开 change。

- [Risk] 从单条全局配置迁移到多 provider + 多模型 + preset 绑定，会引入 migration 和接口切换成本。
  -> Mitigation: 明确 migration 方案，前端同步切 API，不维持长期双写。

- [Risk] 如果把 provider 配置和 preset 分配堆在一个视图里，页面会再次退化成大表单。
  -> Mitigation: 用 provider 管理视图 + 固定任务模型预设视图分层承接。

- [Risk] fallback 一旦做成用户可编排，很快会演变成 policy 系统。
  -> Mitigation: 本轮只实现固定顺序的最基础 fallback，不提供用户自定义链路编辑。
