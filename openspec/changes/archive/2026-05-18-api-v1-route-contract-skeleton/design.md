# Design: 收住 apps/api v1 路由与契约骨架

## 背景

issue #60 将 issue #57 中较大的 API 后端基建方向收窄为一个小范围 API 层契约切片。当前 `apps/api` 已经具备 FastAPI app factory、统一 `code/data/msg/error` 响应信封、request id middleware、全局异常处理、数据库 lifespan 钩子、`/api/v1/health`、`/api/v1/ready`、仅 development 加载的 debug router，以及覆盖 health、readiness、错误响应、validation、404/405、request id 和 production debug gating 的 `TestClient` 测试。

当前缺口不是实现真实事件、插件、审批、Agent、runtime、WebSocket、executor 或交易 endpoint，而是先固定新 API v1 资源的组织方式。如果这层约定继续隐含，后续 endpoint 会各自决定 router 注册、DTO 位置、sample/mock 数据位置、OpenAPI tag、`response_model` 和契约测试方式，导致 API 层从一开始分叉。

本设计只固定最小 API v1 骨架，不把 sample data 提升为生产业务状态，也不发布静态 OpenAPI artifact。

相关当前基线：

- `apps/api/src/quantagent/api/main.py`：创建 FastAPI app，注册 middleware、exception handlers、数据库 lifespan，并直接 include health/debug router。
- `apps/api/src/quantagent/api/routers/health.py`：暴露 `/health` 与 `/ready`，其中 readiness 使用请求级 DB session dependency。
- `apps/api/src/quantagent/api/routers/debug.py`：在 `/debug` 下暴露 debug-only routes，已有 tags 和部分显式 `response_model` 示例。
- `apps/api/src/quantagent/api/responses.py`：定义 `ApiResponse[T]` 和 `ApiErrorDetail`。
- `apps/api/src/tests/test_app.py`：覆盖当前 route、envelope、readiness 和 production debug gating 行为。
- `docs/design/01-tech-stack-and-project-structure.md`：定义 `apps/api` 是 HTTP/API 边界，复杂业务逻辑调用 core/agent。
- `docs/design/08-api-and-websocket-design.md`：要求 API DTO 独立于 ORM model，HTTP API 统一使用 envelope。

## 目标

- 固定最小可发现的 API v1 资源结构：`routers/`、`schemas/`、`providers/`。
- 集中标准 API v1 router 注册方式，同时不替换现有 app factory 或数据库 lifespan。
- 增加一个非业务示例资源 `GET /api/v1/version`，用于展示 DTO、provider、envelope、tag 和 OpenAPI 可见性约定。
- 让 health/ready route 显式参与相同的 `response_model` 与 tag 约定，同时保持现有运行时语义。
- 通过 FastAPI runtime OpenAPI schema 测试验证契约，不生成静态 OpenAPI artifact。
- 在 `apps/api/README.md` 中记录新增 route 的流程和最小验证命令。

## 非目标

- 不实现 issue #57 或整体 API 后端基建汇合方案。
- 不实现事件、插件、审批、Agent run、tool invocation、runtime health、WebSocket、executor、scheduler、Event Bus 或 live trading endpoint。
- 不新增数据库表、ORM model、migration、repository、audit log 或业务持久化。
- 不在本 change 中引入 `services/` 层。
- 不接入 DeepAgents、插件 registry、worker、scheduler、外部服务、真实凭证或生产系统。
- 不发布或更新 `packages/contracts/openapi/`、generated clients、TypeScript types 或 Zod schema。
- 不把 sample provider 等同于现有请求级 DB session dependency。

## 规范分层与决策状态

### 规范分层

本 change 的规范分层固定如下：

- `specs/api-v1-route-contract-skeleton/spec.md` 定义必须满足的外部行为与验收场景。
- `proposal.md` 定义当前 phase 的范围、非目标和验收意图。
- `design.md` 解释本 phase 已做出的实现决策、边界、失败路径和禁止路径。
- `tasks.md` 定义执行顺序、并行关系和写入边界。

以下内容是派生证据，不是本 change 的契约真源：

- FastAPI runtime `/openapi.json`
- `src/tests/` 中对 OpenAPI 和 route 的断言
- `apps/api/README.md`
- FastAPI/Pydantic 自动生成的 schema component 名称

换言之，`/openapi.json` 用来证明 route/tag/envelope 已正确暴露，但它不反向决定 API 资源应该是什么；README 只负责指导开发者，不定义行为要求。

### 本阶段已定

- 目录职责固定为 `routers/`、`schemas/`、`providers/`。
- 示例资源固定为 `GET /api/v1/version`。
- 标准 API v1 router 通过单一共享注册 helper `register_api_v1_routes` 集中装配。
- `health`/`ready` 继续保留现有运行时含义，只补强显式 `response_model` 和 tags。
- OpenAPI 只做 runtime schema 测试，不提交静态 artifact。

### 待定但不阻塞实现

- 标准 router 注册 helper 的实现细节可以后续微调，但入口名称固定为 `register_api_v1_routes`，并且必须是单一、可发现的共享注册入口。
- `health`/`ready` 的成功 DTO 是使用局部窄 schema 还是共享 health schema；只要可观察响应体与现有测试兼容即可。
- 后续真实业务资源是否需要 `services/`、`usecases/` 或其他 orchestration 边界；本 change 不预置答案。

### 延后到后续 change

- 静态 OpenAPI artifact、generated client、TypeScript types、Zod schema。
- API 鉴权、多租户 RBAC、Policy Gate、audit logging。
- plugin registry、Agent runtime、scheduler、Event Bus、executor、WebSocket 或 live trading endpoint。
- 真实业务 repository、service/usecase、持久化和跨系统 orchestration。

## 关键决策

### 目录采用 `routers/`、`schemas/`、`providers/`

`routers/` 只负责 HTTP 边界，包括 path、dependency、status code、tag、`response_model` 和 `ApiResponse[T]` 包装。

`schemas/` 负责 Pydantic request/response DTO。DTO 是 API 契约，不应直接复用 ORM model，也不应在具有契约意义的资源中长期使用临时 dictionary 替代。

`providers/` 负责 sample 或可替换的数据边界。本 change 中 provider 不是 repository、service、unit of work、adapter registry 或 runtime orchestrator。它只表达未来可以被 core repository、runtime adapter、service 或 usecase 替换的位置。

影响：后续真实业务 endpoint 仍可在需要 orchestration、持久化或领域行为时引入 service/usecase，但本骨架不提前制造空抽象。

### 示例资源采用 `GET /api/v1/version`

`version` 名称业务含义低，足以验证 envelope、DTO、provider、tag 和 OpenAPI 行为，同时不会暗示 runtime、Agent、plugin、approval、metadata aggregation、WebSocket、executor 或 trading 能力已经落地。

payload 固定为以下三字段：

- `service`: API 服务名，固定为非空字符串，用于标识当前 API 包。
- `api_version`: API 契约版本，固定为非空字符串，例如 `v1`。
- `version`: 当前 API 包版本或发布版本，固定为非空字符串。

payload 不得包含 runtime health、数据库状态、插件 registry 状态、feature flags、credential、环境密钥、部署内部细节或其他动态运行时数据。

影响：该 route 是契约示例，不是业务状态真源。

### 标准 API v1 router 注册集中到 helper

`main.py` 继续负责 app 创建、middleware、exception handlers 和 lifespan。标准 API v1 routers 应通过单一共享注册 helper `register_api_v1_routes` 集中列出，避免未来资源继续直接在 `main.py` 中手工接线。

该 helper 需要满足：

- 标准 routers 挂载在 `settings.API_V1_PREFIX` 下。
- 标准 routers 的列表位置清晰可发现。
- debug-only router 继续受 `Settings.is_production` gating 控制。
- 不创建新的 app instance，不绕过 `create_app` 中定义的 FastAPI lifespan。

官方路径、回退路径与禁止路径固定如下：

- 官方路径：新的标准 API v1 资源放在 `routers/`、`schemas/`、`providers/` 中，并通过 `register_api_v1_routes` 接入 `create_app()` 创建出的同一个 app 实例。
- 回退路径：现有 `routers/health.py` 与 `routers/debug.py` 可以继续保留原文件位置；`health`/`ready` 可以暂时使用局部窄 DTO；debug router 继续单独受 production gating 控制。
- 禁止路径：新的标准 route 直接在 `main.py` 零散 `include_router(...)`；把示例或未来标准资源挂到 `/debug`；复用 `/ready` 充当 sample provider；以无 schema 契约的临时 dictionary 代替示例资源 DTO。

影响：route 注册变得可发现，同时数据库初始化和关闭仍由 app lifespan 持有。

### 保持 readiness 语义不变

`/api/v1/health` 继续作为 liveness probe，不依赖数据库可用性。

`/api/v1/ready` 继续作为数据库 readiness probe。它应继续使用 `get_db_session`，在数据库已配置时执行最小查询，ready 时返回成功 envelope，在数据库未配置或不可用时返回现有的脱敏 503 envelope。

本 change 可以为 health/ready 增加显式 `response_model` 和 tags，但不能改变它们的运行时含义。

影响：提升 OpenAPI 契约可见性，但不把 readiness 变成 sample provider 或通用 metadata route。

### 只做 runtime OpenAPI schema 测试

本 change 通过测试读取 FastAPI `/openapi.json` 来验证 OpenAPI 可见性。测试应确认标准 routes 带有 tags 和 `ApiResponse[...]` 成功响应 schema，并确认 production OpenAPI 排除 debug-only paths。

本 change 不生成或提交静态 OpenAPI 文件。

影响：保持 issue #60 的小范围，同时防止 route/tag/envelope 可见性被误删。

## 契约边界

### API 边界

本 change 的公开 API 契约是：

- `GET /api/v1/version` 存在，并返回 `ApiResponse[VersionResponse]`。
- `GET /api/v1/health` 保持当前成功响应体，并暴露显式 `ApiResponse[...]` response model 和 tag。
- `GET /api/v1/ready` 保持当前成功和 503 readiness 行为，并暴露显式成功 response model 和 tag。
- `/api/v1/debug/*` 只在非 production 环境可用，并且不出现在 production OpenAPI schema 中。

### Schema 边界

`version` response DTO 放在 `apps/api/src/quantagent/api/schemas/` 下。该 DTO 是 route 放入 `ApiResponse[T]` 中的稳定数据形状。

health/ready 可以使用本地窄 DTO，也可以使用共享 health schema 类型，但可观察响应体必须保持与现有测试兼容。

### Provider 边界

`version` provider 放在 `apps/api/src/quantagent/api/providers/` 下。它只能返回静态或 sample API 信息，不能打开 DB session、读取 credential、调用 core/agent/plugin runtime、访问生产服务或表达业务运行状态。

### Runtime 与 Persistence 边界

本 change 不改变数据库生命周期归属。`initialize_database`、`shutdown_database` 和 `get_db_session` 保持现有职责。provider 骨架不能复制或替换请求级 DB session 处理。

### Frontend 与 Contract Artifact 边界

前端可以在开发时读取 runtime OpenAPI schema，但本 change 不创建 generated frontend types、client、Zod schema 或已提交的 OpenAPI artifact。

### 契约真源与派生视图边界

本 change 中，API 路径、DTO 形状、`response_model` 和统一 envelope 行为是契约真源；README、OpenAPI 展示和测试断言只是验证和展示这些契约的派生视图。

因此：

- 自动生成的 OpenAPI component 命名不应被视为稳定外部契约。
- 测试应优先断言 path、tag、成功 envelope 结构和关键字段，而不是紧耦合某个 component 名称。
- README 不得宣称任何未在 spec/proposal 中承诺的能力已经完成。

## 数据流与控制流

标准请求流程：

```text
client
  -> create_app() 创建的 FastAPI app
  -> RequestIdMiddleware
  -> 已注册的 API v1 router
  -> route handler
  -> version route 可调用 sample provider
  -> schema DTO
  -> ApiResponse.success(...)
  -> FastAPI response_model 序列化
```

readiness 请求流程：

```text
client
  -> /api/v1/ready
  -> get_db_session(request)
  -> SELECT 1
  -> ApiResponse.success({"status": "ready"})
```

如果数据库未配置或 readiness 查询失败，现有 exception handling 返回脱敏的 `SERVICE_UNAVAILABLE` envelope。该失败路径属于现有 API 行为，必须继续由测试覆盖。

应用启动与关闭流程：

```text
create_app(settings)
  -> 定义 lifespan
  -> FastAPI(..., lifespan=lifespan)
  -> 注册 middleware 和 exception handlers
  -> 注册标准 API v1 routers
  -> 按环境条件注册 debug router
```

router 注册 helper 只在 app 已创建后参与注册，不拥有 lifespan setup。

## 同步模型、失败路径与可观测性

### 同步模型

本 change 只引入同步 request/response 路径，不引入后台任务、事件发布、异步编排、取消语义、重试队列或跨请求状态机。

- `version` route 是单次同步读取 sample provider 并返回 envelope。
- `health` route 是单次同步 liveness 响应，不依赖数据库。
- `ready` route 是单次同步数据库探针，最多执行一次最小查询。

这意味着本阶段不需要定义 job state、重试顺序、补偿事务或取消传播规则。

### 失败路径

当前 phase 明确只有以下失败路径需要被设计和测试覆盖：

- app startup 期间若 router 注册 helper 导入或装配失败，应直接使应用启动失败，而不是静默跳过部分 routers。
- `version` provider 只返回进程内静态或 sample 数据，不允许增加数据库、网络、凭证或 runtime 依赖，因此不设计额外回退链路、重试逻辑或降级数据源。
- `ready` 继续通过 `get_db_session` 和 `SELECT 1` 暴露数据库 readiness；数据库未配置或查询失败时，继续返回脱敏的 `SERVICE_UNAVAILABLE` envelope。
- `health` 继续保持与数据库状态解耦；即使 session factory 损坏，也不能因此变成失败探针。

禁止的失败处理方式：

- 在 `version` route 中吞掉真实实现错误后伪造一个看似成功的默认 payload。
- 在 `ready` 失败时回退到 sample provider、缓存状态或环境变量推断结果。
- 为了让 OpenAPI 测试通过而把 debug-only route 暴露到 production app。

### 可观测性与审计边界

本 change 只沿用现有 API 包已有的最小可观测性边界，不额外引入新的审计系统：

- 继续依赖现有 `RequestIdMiddleware` 传播 `X-Request-ID`。
- 继续依赖全局异常处理输出统一错误 envelope 与脱敏错误信息。
- readiness 失败继续记录数据库不可用告警，但不输出敏感连接信息。
- 不新增 audit log、trace pipeline、metrics registry 或生产告警集成。

## 备选方案

### `routers/`、`schemas/`、`services/`

不采用。service 层适合隔离真实 orchestration、持久化或领域行为。本 issue 只需要替换点和契约示例。现在增加 service 会制造空架构，并让 API 包看起来比实际更完整。

### 同时增加 `providers/` 和 `services/`

不采用。该方案对本 issue 过重，会增加文件数量和架构表面积，但没有真实业务 workflow 支撑这些职责。

### 示例 route 使用 `runtime`

不采用。`runtime` 会暗示 runtime health 或 Agent runtime 已接入，和本 issue 非目标冲突。

### 示例 route 使用 `metadata`

暂缓。`metadata` 边界模糊，后续容易塞入环境状态、feature flags、runtime 状态等杂项。`version` 更窄。

### 当前提交静态 OpenAPI artifact

不采用。静态 artifact 需要生成命令、diff 策略、版本管理、前端消费和 CI 规则。对本骨架来说，runtime schema 测试已经足够。

## 风险与缓解

- 风险：sample provider 被误认为生产数据访问层。
  缓解：provider 只返回静态或 sample 数据，命名保持窄边界，README 明确说明其替换点定位，测试只覆盖 API 契约行为。

- 风险：router 注册重构破坏数据库 lifespan 或 readiness。
  缓解：lifespan 继续留在 `create_app`；保留并扩展数据库未配置、查询失败、配置成功和资源清理测试。

- 风险：debug routes 泄露到 production OpenAPI。
  缓解：同时测试 production route 访问和 production `/openapi.json` path exclusion。

- 风险：version payload 变成环境或 runtime 状态杂项入口。
  缓解：`VersionResponse` 保持小而非业务化；拒绝暴露 runtime、plugin、Agent、database、feature flag、credential 或部署状态字段。

- 风险：OpenAPI 断言过度依赖 Pydantic/FastAPI 生成的 component 名称。
  缓解：优先断言 path、tags、response content，以及存在 `ApiResponse` schema 引用或展开结构；不要在没有必要时绑定精确 component 名称。

## 迁移与发布

不需要数据迁移或生产发布步骤。

实现应作为一个小型 API 包变更交付：

1. 增加 `schemas/`、`providers/` package 和标准 router 注册 helper。
2. 增加 version DTO、provider 和 router。
3. 为 health/ready 增加显式 response model 和 tags。
4. 扩展 route 与 OpenAPI 契约测试。
5. 更新 `apps/api/README.md`。

现有客户端不应感知到 `/api/v1/health`、`/api/v1/ready`、request id header、错误 envelope 或 production debug gating 的破坏性变化。

## Harness 策略

主要验证：

- `cd apps/api && uv run python -m unittest discover -s src/tests`
- `openspec validate api-v1-route-contract-skeleton --type change --strict --json`

目标测试期望：

- `GET /api/v1/version` 返回 `code/data/msg/error`，其中 `code == 0` 且 `error == null`。
- development `/openapi.json` 包含 `/api/v1/version`、`/api/v1/health` 和 `/api/v1/ready`，并带有 tags 和成功响应 schema。
- production `/openapi.json` 排除 `/api/v1/debug/*`，同时保留标准 API v1 paths。
- 现有 readiness 测试继续覆盖数据库未配置、查询失败、配置成功、脱敏 503 envelope 和 lifespan cleanup。

验证不应要求 live PostgreSQL、外部网络、真实 credential、Playwright、生产部署或 live trading。

## 决策待办

以下问题有意留给后续 issue：

- 真实业务资源落地时，orchestration 应位于 API-local services、core usecases、runtime adapters 还是其他边界。
- 何时发布 `packages/contracts/openapi/quantagent.openapi.json`，以及如何执行 generated artifact diff。
- 前端 TypeScript clients、generated types 和 Zod schema 如何生成与版本化。
- API authentication、多租户 RBAC、Policy Gate 和 audit logging 如何引入。
- WebSocket 或 realtime topic contracts 如何与 REST resources 集成。
- plugin registry、Agent runtime、scheduler、Event Bus 和 executor endpoints 在底层能力完成后如何暴露。
