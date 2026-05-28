# AGENTS.md

## 角色与目标

你是在 `apps/api/` 内协作的 AI 编程助手，目标是维护 QuantAgent 的 FastAPI 应用边界。

`apps/api` 是 QuantAgent 的 FastAPI 服务入口，只负责 HTTP/API 传输层：接收请求、做传输层校验与响应封装、接入中间件和路由，把业务能力编排到合适的 package 层。这里可以放路由、请求生命周期、中间件、异常处理、依赖注入和 API 私有配置；不要把核心领域逻辑、插件 Registry、Agent workflow、交易/策略判断、共享数据库基础设施长期沉淀在这里。

## 项目概览

QuantAgent 是事件驱动的量化智能系统。`apps/api` 当前处于 API v1 基础骨架阶段，重点维护应用启动、路由注册、中间件、响应信封、异常处理、数据库就绪探针和 OpenAPI 契约等传输层能力。

本目录技术栈保持简单：`uv + Python + FastAPI + Pydantic`。数据库 engine/session 创建复用 `quantagent-core`，API 层只负责应用生命周期挂载、请求级 session 依赖和 readiness probe。Docker 运行入口复用仓库根目录 `Dockerfile` 和 `docker-compose.yml`。

本文件只记录影响 Agent 行为的本地约束；项目说明和架构细节优先放到 README、OpenSpec 或设计文档。新规则只有在重复影响开发质量或跨任务复用时才写入本文件。

## 本地规则优先级

- 本文件补充并收紧仓库根目录 `AGENTS.md`；仅在同类本地约束更具体时优先适用。
- monorepo 采用渐进式 `AGENTS.md` 策略：越靠近目标代码的规则优先级越高；下层规则只补充或收紧上层规则。
- `apps/api/README.md` 是本目录运行和开发说明的补充来源；当它与本文件不冲突时应一起遵守。

## 关键目录索引

以下是影响 API 边界判断的关键路径索引，不是完整文件清单。

```text
apps/api/
├── AGENTS.md              # API 本地协作规则
├── README.md              # 启动与本地开发说明
├── pyproject.toml         # API 包定义与入口
└── src/
    ├── quantagent/
    │   └── api/
    │       ├── main.py        # FastAPI app 工厂和运行入口
    │       ├── config/        # API 本地配置
    │       ├── db.py          # 应用生命周期数据库初始化与请求级 Session 依赖
    │       ├── http/          # HTTP 传输层基础能力
    │       ├── auth/          # API 私有 Cookie Session 鉴权
    │       ├── schemas/       # API request/response DTO
    │       ├── providers/     # sample data 或可替换 provider seam
    │       └── routers/v1/    # 标准 API v1 路由与注册真源
    └── tests/                 # API 测试
```

## 本地工作流规范

### 变更前

- 先阅读本文件、`apps/api/README.md`、目标模块现有实现和相关测试。
- 涉及行为、架构或跨文件契约时，遵循仓库根目录 `AGENTS.md` 中的 OpenSpec 规则；本文件不重复维护 OpenSpec 流程细节。
- 发现需求会跨到 `packages/core`、`packages/agent`、`packages/plugin-sdk`、`packages/contracts` 或其他 app 时，先明确边界，再动手实现。

### API 边界

- 路由函数保持薄层：负责 HTTP 参数、DTO、状态码、响应信封和依赖注入，不承载可复用领域流程。
- 不在 API 层写需要被 worker、scheduler、插件或前端复用的核心逻辑。
- 可复用的数据库、运行时配置、领域错误、Agent 调用、插件协议和跨端契约优先沉淀到对应 package。
- 核心领域逻辑、共享数据库能力、跨应用配置和可复用基础设施应下沉到 `packages/core`。
- 涉及状态变化、审计、权限、插件生命周期、数据库写入、外部适配或多步骤业务流程时，必须有明确的 service/provider/repository/port 边界，不能把流程塞进 router 函数。
- Repository 或 storage port 只在存在真实持久化、跨调用复用、插件隔离或可替换存储需求时引入；简单 sample provider 不为“看起来专业”提前堆抽象。
- 新增公开接口默认放在 `/api/v1` 前缀下，除非已有 spec 明确要求其他版本或路径。
- 新增业务 API 时遵守 `docs/design/08-api-and-websocket-design.md` 的资源边界：REST 资源为主，副作用操作放在资源下的 `actions` 路径。
- 标准 API v1 routes 统一通过 `quantagent.api.routers.v1.register.register_api_v1_routes` 注册；不要在 `main.py` 零散新增 `include_router(...)`。
- `debug` 路由只能用于非生产诊断；新增调试入口必须保持 `APP_ENV=production` 下不可见，并且生产 OpenAPI 不应暴露 debug 路径。
- `GET /api/v1/health` 是存活探针，不应依赖数据库、外部服务或业务表结构。
- `GET /api/v1/ready` 是数据库 readiness probe，只验证已配置数据库可达；不要把 sample provider 和请求级 DB session dependency 混在一起。
- `GET /api/v1/version` 是最小非业务示例，只展示 DTO、provider、响应信封和 OpenAPI 契约；不要把它扩展成 runtime、plugin、approval、Agent、tool invocation、WebSocket、broker、live trading 或业务 endpoint family。
- WebSocket 或实时通道只负责状态变化通知，不替代 REST 查询和数据库状态真源。
- 高风险动作即使来自前端按钮或 AI 文本，也必须经过后端 Policy Gate。

### 路由骨架

- request/response DTO 放在 `src/quantagent/api/schemas/`，保持 API 契约独立于 ORM model 和内部领域对象；不能直接返回 SQLAlchemy model。
- API DTO、ORM model、领域对象、插件 DTO 和响应 envelope 必须保持分层；需要转换时显式写 mapper/helper，不用数据库字段或内部对象形状冒充公开契约。
- 当前 `src/quantagent/api/providers/` 只用于 sample data 或轻量替换点；需要数据库访问、外部服务调用、credentials、runtime 状态或核心领域逻辑时，应先通过 OpenSpec 明确边界，并优先下沉到 package 层。
- route 应显式声明 FastAPI `response_model=ApiResponse[T]` 和 OpenAPI `tags`。
- 新增 API v1 route 时，按 `schemas/` DTO、`providers/` seam、`routers/` route、`register_api_v1_routes` 注册、`src/tests/` 运行时和 OpenAPI 契约测试的顺序落地。
- 新增或修改跨前端契约时，需要同步更新 `packages/contracts`、OpenAPI 或 JSON Schema 中的对应定义作为契约真源，不能只改 API 侧临时返回字段而不更新契约。
- 本包当前不生成 static OpenAPI artifact、generated client、TypeScript types 或 Zod schema；不要为单个 route 局部引入生成链路。

### 响应与错误

- HTTP API 应逐步收敛到 `code/data/msg/error` envelope；成功响应沿用 `ApiResponse.success(...)`，不要让路由返回裸业务对象作为长期 API。
- 错误响应保持 `code/data/msg/error` 信封，并携带 `error.request_id`；不把底层异常、secret 或连接串原文返回给调用方。
- 新增业务错误优先扩展 `AppError` 体系，避免在路由内散落 ad hoc `HTTPException`。
- OpenAPI 中公开的成功响应也应体现 `code/data/msg/error` 信封，而不是只定义内部 data schema。
- 引入响应结构例外时必须在 PR 中说明原因和兼容策略。

### Request ID 与可观测性

- 所有请求都应保留或生成 `X-Request-ID`，响应头和错误体中的 request id 必须一致。
- 不要在 middleware、异常处理器或日志中记录完整敏感载荷。

### 配置

- API 本地配置放在 `quantagent.api.config`；共享运行时配置或数据库配置放到 package 层。
- `Settings` 继承 `quantagent.core.config.settings.Settings`；当前 API 只补充 `API_V1_PREFIX`、`API_HOST`、`API_PORT` 等传输层配置。新增 API 专属配置时，同步判断它应留在 API 层还是下沉到 `quantagent-core`。
- `apps/api/.env.*` 用于 API 本地多环境配置分层；调整配置加载行为或新增相关约定时，要同时检查实现、样例文件和 README 是否一致。
- 新增环境变量时更新 `apps/api/README.md`；如果 Docker 运行也依赖该变量，同步检查根目录 `docker-compose.yml` 和 `.env.example`。
- 不要硬编码数据库地址、生产端口、secret、部署环境值、生产必需密钥、数据库 URL 或外部服务凭证；通过 Settings 和环境变量读取。

### 数据库

- 不在路由里直接创建数据库 engine；使用应用生命周期和依赖注入管理连接。
- 数据库初始化只在 FastAPI lifespan 中执行，避免测试或脚本在 `create_app(...)` 时提前建立连接。
- API 层通过 `quantagent.api.db.get_db_session` 提供请求级 SQLAlchemy `Session`；依赖函数不应隐式 commit。
- 下游请求处理失败时 session dependency 应 rollback 并 close；正常路径只 close。
- `DATABASE_URL` 缺失或 session factory 未就绪时返回 `ServiceUnavailableError`，不要把连接串、密码、token 或 traceback 泄露到响应体。

### 测试与验证

- API 行为变化必须补充或更新 `src/tests/` 下的测试。
- 新增或调整 route 时同时覆盖运行时响应和 `/openapi.json` 契约，特别是 `response_model`、`tags`、信封结构和生产环境 debug route 隐藏。
- 按 `apps/api/README.md` 中的本地验证命令执行最小验证：`cd apps/api && uv run python -m unittest discover -s src`。
- 当前未定义额外 lint/type/format 命令；后续引入 ruff、mypy、pytest 或其他验证入口时，同步更新本节和 `apps/api/README.md`。
- 改动 Docker、迁移或数据库连接路径时，从仓库根目录验证对应 compose/migration 流程。
- 完成后说明改了哪些文件，以及实际跑过哪些验证；如果因为环境缺失无法验证，要明确说明缺口。

## 文档维护

- 新增路由、环境变量、启动方式或生产/开发差异时，同步更新 `apps/api/README.md`。
- 新增 API 子目录并形成独立职责时，优先补充简短 README 或在本文件目录索引中补充说明。
- 当 README 或实现中的 API skeleton 约定变化时，同步检查本文件，避免 Agent 继续遵循过期边界。
