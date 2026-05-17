# Change: 收住 apps/api v1 路由与契约骨架

## 来源

- GitHub issue: https://github.com/BqLee-AI/QuantAgent/issues/60
- Issue 标题：`[DEV] 收住 apps/api v1 路由与契约骨架`
- Labels: `area:api`, `complexity:small`, `priority:medium`, `status:ready`, `type:enhancement`
- 状态：OPEN

## Issue 归一化

本 change 只关闭一个问题：在不新增业务数据库读写、Agent runtime、插件 registry 或 WebSocket runtime 的前提下，固定 `apps/api` 的 API v1 router、DTO schema、provider 替换点和契约测试骨架。

它现在重要，是因为 `apps/api` 已有 FastAPI app 外壳、统一 `code/data/msg/error` 响应、全局异常处理、`X-Request-ID`、`/api/v1/health`、`/api/v1/ready`、仅 development 加载的 debug router、数据库生命周期接入、请求级 DB session dependency 和基础 `TestClient` 测试；如果继续新增业务 endpoint 而不先固定 API v1 资源层约定，后续 router 命名、`response_model`、OpenAPI tags、sample/mock 数据位置和测试方式会分叉。

影响区域：`api`、`docs`、API 契约测试。

## 当前基线

- `apps/api/src/quantagent/api/main.py` 当前直接注册 health/debug router，并通过 FastAPI lifespan 初始化与释放数据库资源。
- `apps/api/src/quantagent/api/db.py` 已有数据库初始化、关闭和请求级 `get_db_session` dependency；该 dependency 不自动 commit，并在异常路径 rollback/close。
- `apps/api/src/quantagent/api/routers/health.py` 已有 `/api/v1/health` liveness 与 `/api/v1/ready` database readiness，但没有显式 `response_model` 和 tag。
- `apps/api/src/quantagent/api/routers/debug.py` 已有仅 development 加载的 debug router。
- `apps/api/src/quantagent/api/responses.py` 已提供 `ApiResponse[T]` envelope。
- `apps/api/src/tests/test_app.py` 已覆盖 health、ready、数据库未配置/不可用、DB session dependency、错误响应、validation、404/405、request id 和 production debug gating。
- `apps/api/README.md` 已说明启动方式、Docker/数据库、响应信封、`X-Request-ID` 和 production 禁用 debug router。

相关设计真相来源：

- `docs/design/01-tech-stack-and-project-structure.md`：`apps/api` 是 FastAPI 主入口，负责 HTTP/API 边界，复杂业务逻辑调用 `packages/core` 和 `packages/agent`。
- `docs/design/08-api-and-websocket-design.md`：API DTO 独立于 ORM model，HTTP API 使用统一 `code/data/msg/error` envelope。

## 目标

- 固定 `apps/api` 内 API v1 的最小目录职责：`routers/`、`schemas/`、`providers/`。
- 提供一个低风险、非业务含义的 API v1 示例资源，固定 `VersionResponse(service, api_version, version)`、`ApiResponse[T]`、显式 `response_model`、tags 和 OpenAPI 可见性约定。
- 增加 sample provider 替换点，表达未来接入 core repository、runtime adapter 或更正式 service/usecase 的边界。
- 把 API v1 router 注册收敛到单一共享 helper `register_api_v1_routes`，明确常规 router 与 debug-only router 的装载方式，同时不破坏现有 FastAPI lifespan 数据库初始化与释放。
- 通过契约级测试验证 API v1 route 的 path、tag、schema、统一 envelope，以及 production 下 debug router 不暴露。
- 在 `apps/api/README.md` 中说明如何新增一个 API v1 router，并写入最小验证命令：`cd apps/api && uv run python -m unittest discover -s src/tests`。

## 非目标

- 不实现 issue #57 的整体 API 基建汇合设计。
- 不实现事件、插件、审批、Agent run、tool invocation、runtime health、WebSocket 或管理端真实业务 endpoint。
- 不扩展 PR #70 已有数据库生命周期、readiness 和 session dependency 到业务持久化能力。
- 不创建数据库表、ORM model、migration、repository、unit of work 或 audit log。
- 不接入 DeepAgents、插件 registry、worker、scheduler、Event Bus 或真实外部服务。
- 不实现生产级鉴权、多租户 RBAC、Policy Gate、真实 executor 或 live trading。
- 不提交静态 OpenAPI artifact，不生成 OpenAPI client、TypeScript types 或 Zod schema。
- 不引入 `services/` 层。

## 已定决策

- 目录采用 `routers/` + `schemas/` + `providers/`。`providers/` 在本阶段只表示替换点，不暗示 API 层已经有成熟业务 service。
- 示例资源采用 `GET /api/v1/version`。避免使用 `runtime`、`metadata` 等容易让人误以为真实运行时或业务能力已落地的名称。
- `VersionResponse` 字段固定为 `service`、`api_version`、`version`；其中 `service` 和 `api_version` 是稳定标识字段，`version` 是非空字符串，且不允许额外字段。
- 标准 API v1 注册入口固定为 `quantagent.api.routers.register.register_api_v1_routes`。
- OpenAPI 本阶段只做 FastAPI runtime schema 测试，不写入 `packages/contracts/openapi/` artifact。
- `health` 和 `ready` 可以被纳入统一注册与契约测试，但不迁移成业务资源。
- `ready` 是 PR #70 已有的数据库 readiness 探针，不作为本 change 的 sample provider 示例，也不代表业务数据库资源已经落地。
- debug router 继续只在非 production 环境加载，并且 production OpenAPI schema 不应包含 debug-only path。
- README 中应记录 API 测试的默认最小验证命令：`cd apps/api && uv run python -m unittest discover -s src/tests`。

## 变更内容

- 新增 `schemas/` 和 `providers/` 目录，以及一个最小 sample provider。
- 新增非业务示例资源 `GET /api/v1/version`。
- 新增或调整共享 API v1 router 注册 helper `register_api_v1_routes`，集中注册常规 router，并保留 debug-only router gating。
- 为 health/ready/version 显式声明 `response_model` 与 tags。
- 增加 OpenAPI 契约测试，验证 path、tags、envelope schema、lifespan/DB readiness 行为仍保持既有边界，以及 production 下 debug router 不暴露。
- 更新 `apps/api/README.md`，说明新增 API v1 router 的目录、注册、provider 替换点、测试要求、最小验证命令与非目标。

## 验收标准

- 后续开发者可以按 README 与代码示例新增一个 API v1 router，而不需要重新决定目录、注册和测试方式。
- API v1 router 的成功响应继续使用 `ApiResponse[T]` envelope；错误响应继续由统一异常处理输出。
- OpenAPI 中能看到 `GET /api/v1/version` 的 path、tag 和 envelope schema，且其 data schema 只包含 `service`、`api_version`、`version`。
- `/api/v1/health` 继续可用，并通过显式 `response_model` 暴露统一 envelope 契约。
- `/api/v1/ready` 继续保留数据库 readiness 语义，并通过显式 `response_model` 暴露统一 envelope 契约；数据库未配置或不可用时的 503 行为不被本 change 改坏。
- API v1 router 注册 helper 不破坏现有 FastAPI lifespan 中的数据库初始化与释放。
- production app 中不暴露 `/api/v1/debug/*`，production OpenAPI schema 中也不包含 debug-only path。
- provider/sample 数据只作为替换点存在，不伪装成真实数据库、Agent runtime 或插件 registry。
- `apps/api/README.md` 明确记录最小验证命令：`cd apps/api && uv run python -m unittest discover -s src/tests`。

## 失败信号

- 新增 router 仍然需要在多个地方手工猜测注册方式、tag、`response_model` 约定，或 `VersionResponse` 字段。
- 示例 provider 写入业务状态、数据库访问、核心领域逻辑、runtime 健康状态或插件 registry 状态。
- 示例 provider 与 PR #70 的 DB session dependency 概念混淆，让人误以为 sample resource 已经接入真实业务数据库。
- 示例路由名称或返回内容暗示事件、插件、审批、Agent run、runtime health 或 WebSocket 已经可用。
- router 注册 helper 或重构破坏现有 `/api/v1/ready` 的数据库 readiness 行为、503 envelope 或 lifespan 资源清理。
- OpenAPI 契约测试缺失，导致 route/tag/schema/envelope 只能靠人工检查。
- debug/test-only 路由在 production app 或 production OpenAPI schema 中暴露。
- README 没有给出本 API 包的最小测试命令，导致后续新增路由时缺少默认验证入口。
- 变更需要外部网络、真实 PostgreSQL、真实凭证或生产服务才能验证。

## 依赖与顺序

- 无外部服务依赖，可在当前 `apps/api` 基建上独立完成。
- 必须先固定 router 注册 helper 和目录职责，并确认它不影响 PR #70 已有数据库 lifespan/readiness，再新增示例资源与文档，避免 README 和测试描述不存在的结构。
- API 代码、测试、README 可以在注册 helper 稳定后分支推进，但最终需要一次 review checkpoint 检查示例资源边界。

## 待确认问题

当前无阻塞问题，方案固定如下：

- 目录采用 `routers/` + `schemas/` + `providers/`。
- 示例资源采用 `version`。
- OpenAPI 仅做 runtime schema 测试，不提交静态产物。
- README 记录最小验证命令：`cd apps/api && uv run python -m unittest discover -s src/tests`。
- 本 change 不接入真实 business/service 层。
- PR #70 已有的 `/api/v1/ready` 保持数据库 readiness 探针定位，不替代 `version` 示例资源。

## 人工审核门禁

本 proposal、`tasks.md` 和 spec delta 是 implementation 前的 review target。实现必须等待维护者明确批准。

## 验证

- `cd apps/api && uv run python -m unittest discover -s src/tests`
- `openspec validate api-v1-route-contract-skeleton --type change --strict --json`
