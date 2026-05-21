# Change: 收敛 API v1 public allowlist 与默认 protected 路由边界

## Issue

- GitHub issue: https://github.com/BqLee-AI/QuantAgent/issues/92
- Title: `[DEV] 收敛 API v1 public allowlist 与业务路由默认 protected 强约束`
- Labels: `type:feature`, `complexity:medium`, `area:api`, `priority:high`, `area:risk`, `status:blocked`, `area:openspec`
- State: OPEN

## 背景 / 为什么现在做

PR #87 已经为 `apps/api` 落地本地单用户 Cookie Session 鉴权闭环，包括 `get_current_actor`、`require_capability`、`require_csrf`、401/403 envelope、`/auth/login`、`/auth/logout` 和 `/me`。

但 #87 的 review thread 留下一个安全边界缺口：当前代码仍依赖后续业务 router 显式添加 auth dependency，没有代码级机制保证“public allowlist + 业务路由默认 protected”。这与 #86 / PR #87 OpenSpec 和 README 中“业务 API 默认 protected”的目标不完全一致。

如果这个缺口不单独收住，后续新增 runtime、plugin、secret、approval、executor 等业务 API 时，只要某个 router 忘记接入 `get_current_actor`、`require_capability` 或 `require_csrf`，就可能默认匿名暴露。

## 问题定义

API v1 route 注册边界需要成为可审核、可测试的安全控制面：

- 哪些 route 是 public 必须显式列入 allowlist。
- 未列入 allowlist 的 API v1 route 默认需要有效 session。
- capability guard 和 CSRF guard 继续用于细粒度权限和写操作保护。
- debug route 不能因为只在非 production 注册就绕过默认 protected 原则。

当前稳定 spec 已经声明“业务 routes 默认 protected”，但实现边界缺少可执行的 registration 策略和对应测试口径。本 change 将该语义从原则收敛为可落地的注册与验收约束。

## 目标

- 明确定义 API v1 public allowlist，并要求代码和测试可检查。
- 让非 public 的 API v1 route 默认要求有效 session。
- 将 `POST /api/v1/auth/logout` 纳入默认 protected 机制，并继续保留 CSRF guard。
- 非 production debug routes 仍只在非 production 注册，但注册后不作为 public route。
- 保留 #87 的 `require_capability` 和 `require_csrf`，不把它们合并成粗粒度全局检查。
- 补齐后续实现所需的 runtime behavior tests、registration tests 和 OpenAPI/debug route 测试口径。

## 非目标

- 不重新设计 Cookie Session 鉴权本身。
- 不引入多用户、RBAC、OAuth、SSO、多租户或数据库 session 表。
- 不实现 runtime、plugin、secret、approval、executor 等业务接口。
- 不实现完整 Policy Gate、audit persistence 或高风险动作业务流。
- 不把 capability guard 或 CSRF guard 替换为单一全局 dependency。
- 不把 frontend 隐藏入口作为权限边界。
- 不新增 static OpenAPI artifact、generated client、TypeScript types 或 Zod schema。

## 影响范围

- `apps/api` API v1 route registration boundary。
- `openspec/specs/api-cookie-session-auth/spec.md` 的 public/protected route policy。
- 后续实现阶段的 route runtime tests 和 OpenAPI/debug tests。
- `apps/api/README.md` 中 auth route 与默认 protected 说明。

## 依赖和风险

- 依赖 PR #87 已合入 `main`，以复用 auth dependency、settings、错误 envelope 和 auth routes。
- 风险：如果用 path middleware 实现，可能和 FastAPI dependency、OpenAPI security 表达、测试 override 和 debug route 注册产生耦合。
- 风险：如果只靠文档 allowlist，新增业务 route 仍可能绕过默认 protected。
- 风险：如果默认 protected 误伤 health、ready、version 或 login，会影响探针、本地启动和登录流程。

## 实施结论

- public allowlist 采用显式 registration boundary 管理，优先使用专门 helper 让每个 API v1 router 声明 public 或 protected。
- protected routers 在注册时注入 `get_current_actor` 或共享 session dependency；单个 route 自己手写 `Depends(get_current_actor)` 不能算作满足“默认 protected”。
- `POST /api/v1/auth/login` 是 public；`POST /api/v1/auth/logout` 不是 public，先经过默认 session guard，再执行 `require_csrf`。
- 非 production debug routes 仍保持 production 不注册、不出现在 production OpenAPI；非 production 下按 protected route 处理，development auth bypass 可按 #87 语义提供本地便利。
- OpenAPI cookie security scheme 可作为实现阶段 opportunistic enhancement；本 change 的必须项是 runtime 强约束和测试。

## 验收口径

必须成立：

- public allowlist 在 OpenSpec、代码和测试中一致。
- public allowlist 有单一代码声明位置；README 或 OpenAPI 只能作为说明和证据，不能成为权限真源。
- 匿名访问 `GET /api/v1/health`、`GET /api/v1/ready`、`GET /api/v1/version` 仍成功。
- 匿名访问 `POST /api/v1/auth/login` 仍可执行登录流程。
- 匿名访问未列入 public allowlist 的 API v1 route 返回 HTTP 401，且错误使用 `code/data/msg/error` envelope。
- 带有效 session 访问同一 protected route 成功。
- `POST /api/v1/auth/logout` 缺 session 返回 401；有 session 但缺失或错误 CSRF token 仍被 CSRF guard 拒绝。
- 需要 capability 的 route 仍在 session 之后执行 capability guard，缺 capability 返回 403。
- production OpenAPI 不暴露 debug-only paths。

失败信号：

- 新增 API v1 业务 route 忘记加 dependency 后仍能匿名 200。
- public allowlist 只存在文档里，代码和测试无法验证。
- implementation 通过在每个 route 上手写 auth dependency 通过测试，但没有统一 registration boundary。
- 默认 protected 误伤 health、ready、version 或 login。
- debug route 在 production OpenAPI 中可见。
- 默认 protected 实现绕过 capability 或 CSRF 的细粒度语义。

## 验证要求

- OpenSpec: `openspec validate enforce-api-v1-protected-routes --type change --strict --json`
- 实现阶段 API tests: `cd apps/api && uv run python -m unittest discover -s src/tests`
