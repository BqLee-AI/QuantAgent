# apps/api Review Overview

本文件是 `apps/api` 变更的 AI Code Review 索引。先用 changed files 和 diff 识别场景，再加载未来对应细则；当前只定义导航和核心审查问题。

主要真源：

- `apps/api/AGENTS.md`
- `docs/design/08-api-and-websocket-design.md`
- `.agents/skills/references/engineering-quality-gate.md`

## 场景索引

| 场景 | 触发信号 | 未来细则 | 核心审查问题 |
| --- | --- | --- | --- |
| Router 边界 | `routers/**`、新增 endpoint、actions endpoint、route registration | `router-boundary.md` | route 是否保持 HTTP 薄层；是否把业务流程、数据库写入、插件生命周期或高风险动作塞进 router |
| DTO / envelope / OpenAPI | `schemas/**`、`ApiResponse`、`response_model`、OpenAPI 测试 | `dto-envelope-and-openapi.md` | request/response DTO 是否独立；是否返回 `ApiResponse[T]`；OpenAPI 是否体现 envelope |
| Auth / Session / CSRF | `auth/**`、login/logout/refresh、cookie session、capability、actor | `auth-session-csrf.md` | actor 是否来自后端 session；cookie/CSRF/capability 失败路径是否清晰；高风险动作是否可审计 |
| Error / Request ID / Observability | `http/errors.py`、`http/exceptions.py`、`http/middleware.py`、异常处理器 | `errors-request-id-and-observability.md` | `X-Request-ID` 是否一致；错误是否统一 envelope；是否泄露 secret、连接串或 traceback |
| DB session / lifespan | `db.py`、`main.py` lifespan、health/ready、session dependency | `db-session-and-lifespan.md` | engine/session 是否由生命周期管理；health 是否不依赖 DB；ready 是否只验证 DB 可达；session 是否 rollback/close |
| Debug 与环境 | `routers/v1/debug.py`、APP_ENV、OpenAPI 生产隐藏 | `debug-and-environment.md` | debug route 是否生产不可见；debug 响应是否泄露 env、secret、DB URL 或本地敏感路径 |
| 契约与版本 | 公开 endpoint、response field、error code、schema、OpenAPI tags | `contracts-and-versioning.md` | API v1 资源命名是否稳定；跨端字段变化是否需要同步 contracts / schema / OpenSpec |
| 测试与 readiness | route、schema、middleware、auth、db dependency、OpenAPI 改动 | `tests-and-readiness.md` | 是否覆盖运行时响应和 `/openapi.json`；auth/debug/db 失败路径是否有测试 |

## 选择规则

- 修改 `routers/v1/**` 时，至少加载 router 边界和 DTO / envelope 场景。
- 修改 `auth/**` 时，必须额外检查 request id、错误脱敏和审计 actor。
- 修改 `db.py` 或 lifespan 时，不要只看 API 行为；必须检查 session 生命周期和 `DATABASE_URL` 缺失路径。
- 修改 debug route 时，必须检查生产环境 OpenAPI 和响应脱敏。

## 初始 finding 倾向

优先报告这些问题：

- route 返回 ORM model、裸 dict 或绕过 `ApiResponse`。
- route 内直接创建 engine/session、隐式 commit 或承载业务状态流转。
- 新增 route 未通过 `register_api_v1_routes` 统一注册。
- 错误响应泄露底层异常、连接串、token、secret 或 traceback。
- debug endpoint 在 `APP_ENV=production` 下仍可见。
