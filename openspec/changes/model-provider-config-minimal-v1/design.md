## Context

QuantAgent 当前已有 Agent / workflow 方向设计，长期会通过 ProviderManager 管理多模型供应商、ProviderPolicy、fallback、预算和成本治理。但 issue #156 已明确本轮不做完整治理模块，只先完成最小可运行链路：配置模型供应商、保存 key、调用模型、统计 token。

本 change 涉及 Core、API、DB、Contracts 和 Web，必须满足最新工程质量门槛：实现前明确职责边界、目录蓝图、数据流、失败路径、复用点和验证入口；实现时不能把 router、service、DTO、页面状态和表格逻辑混在同一个大文件里。

## Goals / Non-Goals

**Goals:**

- 支持一条全局 OpenAI-compatible 模型配置，满足本地和早期部署的最小运行需要。
- 支持前端写入 API key，后端加密入库，运行时按需解密调用模型。
- 支持固定 smoke 测试连接，证明 provider、base URL、model 和 key 可用。
- 支持独立 model invocation log，记录基础 token usage 和最近错误摘要。
- 支持 `/models` 最小前端入口，完成配置、测试连接和 token usage 查看。

**Non-Goals:**

- 不实现 ProviderPolicy、`fast` / `balanced` / `reasoning` / `local` 分层。
- 不实现 fallback models、budget、cost governance、限流治理或自动模型发现。
- 不实现 LiteLLM Proxy、模型评估平台、prompt 编辑器或 AgentDefinition 编辑器。
- 不允许插件维护独立模型 key，也不把模型 key 放进插件配置、普通 Settings 或前端 runtime config。
- 不展示完整 prompt、完整模型推理链、完整 provider 请求体 / 响应体或 provider 原始响应。

## Architecture / Boundaries

### Directory Blueprint

- `packages/core/src/quantagent/core/model_config/`
  - `models.py`: 领域枚举、状态值和可被 API / worker 复用的轻量类型。
  - `crypto.py`: Fernet 类 API key 加密 / 解密工具，只处理 secret 加密边界。
  - `orm.py`: `model_configs` 和 `model_invocations` SQLAlchemy ORM model，不作为 API DTO 返回。
  - `service.py`: 全局配置保存、脱敏查询、运行时解密、固定 smoke 调用、invocation log 记录；对外部 provider 调用通过 client port 隔离。
  - `__init__.py`: 导出稳定 service / model API。
- `packages/core/alembic/versions/`: 新增模型配置和 invocation log 迁移；不改写已有迁移历史。
- `apps/api/src/quantagent/api/schemas/models.py`: API request/response DTO，独立于 ORM 和 core 内部对象。
- `apps/api/src/quantagent/api/routers/v1/models.py`: HTTP route、鉴权、CSRF、response envelope、错误映射和 DTO mapper；不承载加密、DB 写入或 provider 调用流程。
- `packages/contracts/schemas/`: 模型配置和 invocation summary 的 JSON Schema，作为跨前后端字段契约参考。
- `apps/web/src/features/models/`
  - `api.ts`: shared API client 的模型配置请求封装，不手写 envelope。
  - `queries.ts`: TanStack Query query / mutation。
  - `errors.ts`: 安全错误摘要格式化，包含 request id。
  - `components/`: 表单、状态统计、invocation 表格和页面组合组件。
- `apps/web/src/routes/_app/(workspace)/models/index.tsx`: TanStack Router 页面入口，只负责挂载 feature 页面组件。

### Backend Boundaries

API route SHALL remain thin: it reads HTTP payload, applies auth / CSRF dependencies, maps DTOs to core service input, wraps `ApiResponse`, and maps safe `ModelConfigServiceError` into existing `AppError` responses.

Core SHALL own the model configuration lifecycle: validation that is not HTTP-specific, encryption/decryption, single global config upsert, provider smoke call, invocation persistence, and status derivation. The provider call is an external adapter boundary behind a `FixedModelCallClient` protocol so API tests and later AgentRuntime can reuse the service without importing FastAPI.

A separate repository class is not introduced in V1 because there is one SQLAlchemy-backed persistence implementation and no alternate storage port yet. The service still keeps persistence and external-call responsibilities explicit enough to split later when AgentRuntime adds runtime invocation paths.

### Frontend Boundaries

The route file SHALL stay a page entry. Business state and server state live in `features/models` through TanStack Query; the page does not call `fetch`, does not unwrap API envelopes, and does not store a long-lived copy of REST snapshots beyond editable form fields.

The UI SHALL use HeroUI primitives for form controls, buttons, switches and tables where practical, and Tailwind utility classes for layout and state styling. CSS modules are avoided for this feature unless a later visual need cannot be expressed cleanly with existing utilities.

## Core Model / API Fields

### Model Config

- `provider_type`: literal `openai_compatible`.
- `name`: display name, max 120 chars.
- `base_url`: optional OpenAI-compatible base URL, max 512 chars.
- `model`: model name, max 200 chars.
- `enabled`: boolean runtime switch.
- `encrypted_api_key`: encrypted secret at rest; never returned through API.
- `status`: derived `configured | missing_key | disabled | failed`.
- `key_status`: derived `configured | missing`.
- `masked_key`: fixed masked marker when configured, not reversible.
- `last_error`: safe code-like provider/config error summary.
- `updated_at`: last config or invocation state update.

### Model Invocation

- `provider_type`, `provider_name`, `model`.
- `status`: `succeeded | failed`.
- `prompt_tokens`, `completion_tokens`, `total_tokens`: nullable when provider omits usage.
- `error_summary`: safe code-like summary, no secret, prompt, provider body or traceback.
- `request_id`, `trace_id`, optional `agent_run_id` for future AgentRuntime association.
- `created_at`.

### API Endpoints

- `GET /api/v1/models/config`: returns current global config status and masked key state.
- `PUT /api/v1/models/config`: saves global config; optional `api_key` is write-only and encrypted before persistence.
- `POST /api/v1/models/actions/test-connection`: runs the fixed smoke prompt using saved config and records one invocation.
- `GET /api/v1/models/invocations`: returns recent invocation summaries, bounded by server-side max limit.

## Data Flow

1. User opens `/models`; Web calls `GET /models/config` and `GET /models/invocations` through shared API client.
2. Web hydrates editable non-secret fields; API key input remains empty and acts only as a replacement field.
3. User saves config; API route validates DTO and CSRF, then calls core service.
4. Core encrypts a provided API key using `MODEL_CONFIG_ENCRYPTION_KEY`, upserts the single global row, and returns a脱敏 config result.
5. User runs test connection; API route calls core service without accepting prompt text.
6. Core checks configured/enabled/key state, decrypts the key briefly, sends fixed smoke prompt to the OpenAI-compatible endpoint, parses optional usage, writes an invocation summary, and returns only safe metadata.
7. Web invalidates config and invocation queries, then displays status, request id, recent error summary and token usage.

## Failure Paths

- Missing database/session factory: API dependency returns existing service-unavailable envelope; model routes do not create engines directly.
- Missing encryption key: save or decrypt returns `MODEL_CONFIG_ENCRYPTION_UNAVAILABLE` / `MODEL_CONFIG_DECRYPT_FAILED` without key, provider payload, connection string or traceback.
- Missing API key: test connection does not call provider, records failed invocation with `MODEL_CONFIG_KEY_MISSING`, and returns structured error.
- Disabled config: test connection does not call provider, records failed invocation with `MODEL_CONFIG_DISABLED`, and returns structured error.
- Provider timeout / unreachable / HTTP error / invalid response: records failed invocation with safe code-like `error_summary`; no full provider body is returned or logged.
- Token usage absent: invocation still records provider/model/status/request id with nullable token counts.
- Permission denied: `/models` is gated by existing secret management capability; UI must show backend errors with request id when available.

## Decisions

### 1. V1 只支持单个全局配置

V1 SHALL 只维护一条全局模型配置。替代方案是支持多个配置和默认项选择，但会引入列表管理、默认配置切换、运行时选择规则和更多 UI 状态，超出“确保能运行”的最小目标。

### 2. Provider 类型固定为 OpenAI-compatible

V1 SHALL 只定义 `openai_compatible` provider 类型。替代方案是同时支持 OpenAI、Anthropic、Ollama 等 provider，但不同鉴权、payload、错误结构和 token usage 解析会把本轮拖成 provider gateway。

### 3. API key 加密入库，查询永不回显

保存配置时，后端 SHALL 接收写入式 `api_key` 字段，并在进入持久化前使用 Fernet 类对称加密。查询配置时，API SHALL 只返回 `key_status`、`masked_key` 或等价脱敏状态，不返回可还原明文。只保存 secret reference 更轻，但已不符合 issue 已确认的“key 要入库”；明文入库不采用。

### 4. Token 统计使用独立 invocation log

V1 SHALL 使用独立 model invocation log 作为 token usage 真源。直接写入 AgentRun 更贴近最终链路，但当前目标是先证明模型配置可以运行；独立 log 能覆盖测试连接和后续 AgentRuntime 调用，并预留 `agent_run_id`。

### 5. 测试连接只发送固定 smoke prompt

测试连接 action SHALL 使用固定 smoke prompt，例如 `Reply with "ok".`。它不接收用户自定义 prompt，不发送真实事件、策略、私有上下文或交易相关内容。

## Reuse / Abstraction Choices

- Reuse existing API auth capability `secret.manage`; V1 不新增 `model.configure` capability，避免在最小实现里扩权限模型。
- Reuse existing `ApiResponse` envelope、`AppError` 映射、`get_db_session` 和 request id middleware。
- Reuse root Python workspace and `packages/core` Alembic entry；只新增必要 `cryptography` 依赖。
- Reuse existing Web shared API client and TanStack Query patterns；不为本页局部引入 generated client。
- Do not introduce LiteLLM Proxy, ProviderPolicy, repository framework, frontend runtime config surface or plugin key surface in V1.

## Validation Strategy

- OpenSpec: `openspec validate model-provider-config-minimal-v1 --type change --strict --json`.
- Core: unit tests for encryption at rest, masked query, runtime decrypt, missing encryption key, disabled/missing-key failures and invocation log.
- API: app tests for auth/CSRF, envelope, no key echo, OpenAPI tags/schema, test connection success/failure and invocation list.
- Web: unit tests for capability policy and model error formatting; build verifies route generation, HeroUI imports and TypeScript contracts.
- Smoke: mock provider client confirms fixed prompt path can record token usage without real API keys.

## Risks / Trade-offs

- [Risk] 单全局配置后续不够支持多模型策略。
  -> Mitigation: V1 明确预留后续 ProviderPolicy change，本 change 不定义多配置选择规则。

- [Risk] API key 入库增加安全和迁移责任。
  -> Mitigation: 强制加密保存、服务端主密钥、脱敏查询、日志不回显，并在测试中覆盖明文泄露路径。

- [Risk] `MODEL_CONFIG_ENCRYPTION_KEY` 缺失会导致配置不可用。
  -> Mitigation: 保存或运行时返回清晰配置错误，不把 key 或内部 traceback 暴露给前端。

- [Risk] OpenAI-compatible token usage 字段在不同网关上不稳定。
  -> Mitigation: token usage 允许缺失时记录为 null，但 provider、model、status、request_id 和错误摘要仍需落 log。

- [Risk] smoke check 产生少量 token 消耗。
  -> Mitigation: prompt 固定且极短，响应只保留状态、token usage 和脱敏错误摘要。
