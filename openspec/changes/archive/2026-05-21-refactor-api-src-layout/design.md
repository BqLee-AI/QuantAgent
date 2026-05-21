## Context

`apps/api` 是 QuantAgent 的 FastAPI HTTP 边界，当前已经具备 API v1 route skeleton、统一响应信封、异常映射、Request ID middleware、数据库 readiness probe 和本地单用户 Cookie Session 鉴权。现有实现仍主要使用早期扁平结构，例如 `quantagent.api.auth`、`responses.py`、`errors.py`、`exceptions.py`、`middleware.py` 和 `routers/register.py`。

issue #105 要求先通过 OpenSpec 明确目录重构边界，再进入实现。该重构必须以当前代码、`apps/api/README.md`、`apps/api/AGENTS.md`、`docs/design/01-tech-stack-and-project-structure.md` 和 `docs/design/08-api-and-websocket-design.md` 为依据；它只整理 API 传输层内部结构，不改变外部 API 行为，也不把核心领域逻辑放入 `apps/api`。

## Goals / Non-Goals

**Goals:**

- 让 HTTP 传输层基础能力、API 私有鉴权和 API v1 route 注册边界在目录结构上可见。
- 让后续新增 API v1 route 时能沿用 `routers/v1/` 注册真源，而不是在 `main.py` 或旧路径零散接入。
- 让本地 Cookie Session 鉴权内部职责拆分清楚，但仍保持 API 私有能力，不提前下沉到 `packages/core`。
- 保持现有 runtime 行为、OpenAPI 契约、响应 envelope、鉴权 allowlist、debug production gating 和 readiness probe 不变。
- 同步更新 README 和 AGENTS，避免后续 Agent 继续按旧目录边界添加代码。

**Non-Goals:**

- 不新增业务 API、runtime API、plugin API、Agent API、WebSocket、executor 或 live trading 能力。
- 不改变 `/api/v1/health`、`/api/v1/ready`、`/api/v1/version`、`/api/v1/auth/login`、`/api/v1/auth/logout`、`/api/v1/me` 的路径、状态码、响应结构或 OpenAPI tags。
- 不改变 public/protected allowlist、session guard、capability guard、CSRF guard、development auth bypass 或 production secure-cookie 校验语义。
- 不引入 `services/`、`repositories/`、`domain/`、`models/`、`usecases/` 等容易暗示 API 层承载核心业务逻辑的占位目录。
- 不新增依赖，不迁移测试框架，不生成 static OpenAPI artifact、前端 client、TypeScript types 或 Zod schema。

## Source of Truth and Boundaries

- 规范真源：本 change 的 `specs/api-src-layout/spec.md` 定义目录重构验收口径；`openspec/specs/api-cookie-session-auth/spec.md` 定义 Cookie Session、capability guard、CSRF、development bypass 等稳定鉴权行为。
- 实现真源：当前 `apps/api/src/quantagent/api/**` 和 `apps/api/src/tests/**` 是迁移输入；实现阶段不得只按文档想象重排不存在的模块。
- 文档真源：实现完成后 `apps/api/README.md` 和 `apps/api/AGENTS.md` 必须反映新目录；它们不是旧路径继续增长的理由。
- 禁止路径：不得通过在 `main.py` 零散新增标准 API v1 `include_router(...)`、在 route 内重复临时 auth dependency、或在 API 层新增业务核心目录来绕过本 change 的边界。
- 兼容路径：旧 import 只允许作为薄 re-export 存在于高风险公共入口；re-export 不能持有新逻辑、状态或分叉行为。

## Decisions

### 1. 使用 `http/` 承接传输层基础能力

`http/` 承接响应信封、API 层错误类型、异常处理注册和 Request ID middleware。它只表达 FastAPI/HTTP 传输层边界，不承载数据库访问、业务流程、插件 Registry、Agent workflow 或交易策略判断。

实现阶段的默认映射是 `responses.py`、`errors.py`、`exceptions.py` 和 `middleware.py` 迁入 `http/` 或其直接子模块；如实现者发现现有文件职责更适合更细拆分，也必须保持在 HTTP 传输层边界内。

替代方案是继续把 `responses.py`、`errors.py`、`exceptions.py` 和 `middleware.py` 放在 `quantagent.api` 根下。该方案短期改动少，但目录无法表达这些文件属于同一传输层基础能力，因此不采用。

### 2. 使用 `auth/` 拆分 API 私有 Cookie Session 鉴权

`auth/` 承接当前 `auth.py` 的现有职责，并按 actor/capability、session/cookie、CSRF/dependency、audit context 拆分。该模块仍属于 `apps/api` 私有鉴权边界，不因为拆目录而升级为共享鉴权包。

实现阶段的默认拆分是把 actor model、capability 常量和 guard、session 签发/解析/刷新、cookie 设置/清理、CSRF 校验、FastAPI dependency 和 audit context 放入 `auth/` 下清晰命名的模块；模块名可以随现有代码形态调整，但不得继续让单个文件承载全部职责。`refresh_session` 这类活动续期能力应留在 session/cookie 边界内，迁移后仍只能基于当前 `CurrentActor` 的 actor id 和 capability snapshot 重签 session，不能绕过 session guard 扩大权限。

替代方案是把鉴权能力下沉到 `packages/core`。当前只有 FastAPI 浏览器 Cookie Session 使用方，没有 worker、scheduler 或其他 package 复用需求；提前下沉会扩大公共契约，因此不采用。

### 3. 使用 `routers/v1/` 表达 API v1 注册边界

标准 API v1 route、debug gating 和 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 继续作为注册真源，但落位到显式的 v1 路由目录。新增标准 API v1 route 应通过该边界注册，不在 `main.py` 零散新增 `include_router(...)`。

实现阶段的默认映射是把当前 `routers/register.py` 和标准 API v1 route 文件迁入 `routers/v1/`；如保留 `routers/__init__.py`，它只作为包边界或必要 re-export，不作为新的注册真源。

替代方案是保留 `routers/register.py` 和 `routers/*.py` 的扁平结构。该方案没有行为问题，但随着 v1 route 增长会继续隐藏版本边界，因此不采用。

### 4. 采用最小兼容 import 策略

实现阶段内部 import 应迁移到新路径；只对高风险公共入口保留薄 re-export，例如历史上容易被测试、脚本或外部调用引用的模块入口。README、AGENTS 和新增代码示例必须指向新路径，避免旧路径继续增长。

高风险公共入口的判定口径是：旧模块路径被 `apps/api/src/tests`、README/AGENTS、仓库内其他 app/package，或可能被外部脚本直接导入的边界引用。仅由 `apps/api` 内部实现互相引用的旧路径，不应因为迁移方便而保留 re-export。

替代方案是全量保留旧路径 re-export。该方案迁移风险最低，但会形成长期双入口。另一个替代方案是不保留任何兼容入口，结构最干净，但对未发现外部引用过于敏感。因此采用最小兼容。

### 5. 文档与测试作为重构完成条件

目录重构不是只让 import 通过。实现 PR 必须同步 README、AGENTS 和测试，使文档目录索引、route 注册说明、auth/http/router 边界与实际代码一致。测试不能通过修改行为断言来适配重构。

替代方案是只迁移源码，文档后补。该方案会让后续 Agent 继续按照旧边界工作，因此不采用。

## Risks / Trade-offs

- [Risk] 目录移动导致 OpenAPI 路径、tags、response_model 或 envelope schema 发生非预期变化。
  → Mitigation: 保留现有 route 定义语义，并运行 API runtime 与 OpenAPI 契约测试。
- [Risk] 旧 import 路径保留过多，导致新旧路径长期并存。
  → Mitigation: 只保留高风险公共入口薄 re-export，新增代码和文档统一指向新路径。
- [Risk] 拆分 `auth.py` 时误改 session、cookie、CSRF、`/me` 活动续期或 capability 行为。
  → Mitigation: 迁移前后复用现有测试断言，特别保留 `/me` 在 session 模式下刷新 HttpOnly cookie 和 `csrf_token`、development bypass 下不签发 session 的断言；新增必要 import 边界测试时不得放宽行为验收。
- [Risk] 新目录被误解为 API 层可以承载业务核心逻辑。
  → Mitigation: README 和 AGENTS 明确禁止新增空的 `services/repositories/domain/models/usecases` 目录，并重申 `apps/api` 只承载 HTTP 边界。
- [Risk] 文档和实际结构再次漂移。
  → Mitigation: 把 README/AGENTS 同步列为实现任务和验收条件，而不是可选收尾。

## Migration Plan

1. 先提交并审核本 OpenSpec-only PR；维护者明确评论“没问题”或批准前，不进入代码实现。
2. 实现阶段先确认现有测试全量可作为基线，再按 `http/`、`auth/`、`routers/v1/` 三条边界迁移。
3. 迁移后运行 API 测试和 OpenAPI 契约检查；如失败，优先定位 import 迁移问题，不通过放宽行为断言绕过。
4. 更新 README 和 AGENTS，使后续新增 route、auth 和 HTTP 基础能力使用新路径。

## Open Questions

- 当前无阻塞问题。旧 import 兼容策略已按“最小兼容”处理，具体保留哪些 re-export 由实现阶段基于上述高风险公共入口口径确认；不得扩大为全量长期双入口。

## Deferred / Out of Phase

- 前端契约生成、static OpenAPI artifact、TypeScript client、Zod schema 和 `packages/contracts` 生成链路不在本 change 内启用。
- 多用户、RBAC、OAuth、SSO、跨 app/worker/scheduler 共享鉴权包不在本 change 内设计或实现。
- runtime、plugin、approval、Agent、tool invocation、WebSocket、executor 和 live trading endpoint family 不因目录重构获得任何新增能力。
