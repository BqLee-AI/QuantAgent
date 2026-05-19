# Tasks: apps/api 单用户 Cookie Session 鉴权闭环

## 状态

当前状态为实现进行中。OpenSpec-only PR 已获认可，开始按本任务图落地并验证实现。

## 任务图

### 阻塞串行路径

- [x] B0. OpenSpec-only artifacts 审核
  - 输入：issue #86、issue #79、`proposal.md`、`design.md`、本 `tasks.md`、spec delta
  - 输出：维护者明确批准进入实现
  - 写入边界：`openspec/changes/add-api-cookie-session-auth/**`
  - 阻塞原因：仓库 workflow 要求行为、架构、跨文件契约变化先审核 OpenSpec；审核通过前不得实现代码、加依赖或修改 API runtime

- [x] B1. 稳定 auth settings 与安全默认值
  - 输入：B0 审核结论、现有 `Settings`、`apps/api/README.md`、Docker/production 默认约束
  - 输出：auth enabled、admin credential、session secret、cookie name、cookie secure/httpOnly/sameSite、session lifetime、CSRF header 等配置；production 禁止弱默认；development-only auth disabled；明确当前 local Docker compose 不等同 production
  - 写入边界：`apps/api/src/quantagent/api/config/**`、`apps/api/README.md`，必要时检查根目录 `.env.example` / `docker-compose.yml`
  - 依赖：B0

- [x] B2. 实现 session 与 CurrentActor 基础
  - 输入：B1 settings、现有 request id middleware、现有 `ApiResponse`
  - 输出：session 签发/校验/过期/清除；CurrentActor DTO 或内部模型；auth disabled development 下的 `local_dev` actor；敏感信息脱敏边界
  - 写入边界：`apps/api/src/quantagent/api/**` 中 auth 相关新模块或 API 私有 helper；不得新增数据库表或 migration
  - 依赖：B1

- [x] B3. 实现固定 capability 集合与 guard
  - 输入：B2 CurrentActor、#79/#86 capability 集合
  - 输出：集中维护的 capability 常量/枚举；local admin capability snapshot；统一 capability guard；禁止 router 手写分散 capability 判断
  - 写入边界：`apps/api/src/quantagent/api/**` auth/capability 相关模块
  - 依赖：B2

- [x] B4. 扩展 401/403 AppError envelope
  - 输入：现有 `AppError`、异常处理、response envelope、request id 行为
  - 输出：`UnauthorizedError` / `ForbiddenError` 或等价错误类型；401/403 HTTP status；`error.code=UNAUTHORIZED` / `FORBIDDEN`；错误体携带 request_id 且不泄露 secret/session
  - 写入边界：`apps/api/src/quantagent/api/errors.py`、`apps/api/src/quantagent/api/exceptions.py`、相关 tests
  - 依赖：B2

- [x] B5. 实现 CSRF 基础契约与 guard
  - 输入：B2 session、B4 errors、默认 header `X-CSRF-Token`
  - 输出：固定 CSRF token 获取口径；login 成功响应和 `/api/v1/me` 返回非敏感 `csrf_token` 快照；protected write route CSRF guard；login 豁免；logout 与写操作必须校验 `X-CSRF-Token`；错误 envelope 不泄露 submitted token、expected token 或 token derivation material
  - 写入边界：`apps/api/src/quantagent/api/**` auth/csrf 相关模块与 tests
  - 依赖：B2、B4

- [x] B6. 实现 auth routes 与注册
  - 输入：B2 session、B3 capability snapshot、B4 errors、B5 CSRF 契约、现有 API v1 router skeleton
  - 输出：`POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/me`；login success 和 `/me` response 包含 `csrf_token`；DTO 放入 `schemas/`；route 显式 `response_model=ApiResponse[T]` 和 tags；通过 `register_api_v1_routes` 注册
  - 写入边界：`apps/api/src/quantagent/api/routers/**`、`apps/api/src/quantagent/api/schemas/**`、`apps/api/src/quantagent/api/routers/register.py`
  - 依赖：B2、B3、B4、B5

- [x] B7. 实现 actor/audit context helper
  - 输入：B2 CurrentActor、request id middleware、B3 capability guard
  - 输出：后续高风险 API 可复用的 actor/audit context helper，包含 actor id/type、capability/request metadata，不含 session/cookie/signature/password/hash/secret
  - 写入边界：`apps/api/src/quantagent/api/**` auth/audit context 相关模块
  - 依赖：B3、B4

### B6 后可并行任务

- [x] P1. 补 route runtime tests
  - 输入：B5/B6 runtime 行为
  - 输出：public route anonymous success；protected route anonymous 401；invalid/expired session 401；login success/failure；login success 返回 `csrf_token`；logout 携带有效 CSRF 后 clears cookie；`/me` valid response 返回 `csrf_token`；`/me` invalid session；auth disabled only in development
  - 写入边界：`apps/api/src/tests/**`
  - 可与 P2/P3 并行：auth route 行为稳定后

- [x] P2. 补 capability 与 CSRF tests
  - 输入：B3 capability guard、B6 CSRF guard
  - 输出：missing capability 403；valid capability success；protected write CSRF missing/invalid/valid；logout CSRF missing/invalid/valid；CSRF token 获取口径固定为 login success 和 `/me`
  - 写入边界：`apps/api/src/tests/**`
  - 可与 P1/P3 并行：写入同一测试文件时实际合并编辑以避免冲突

- [x] P3. 补 OpenAPI 与敏感信息 tests
  - 输入：B4/B5 route schema 和 errors
  - 输出：auth route path/tag/envelope schema；401/403 envelope schema；production debug route 仍隐藏；响应和错误不包含 admin password、hash、session、cookie、signature secret、private policy 或 stack trace
  - 写入边界：`apps/api/src/tests/**`
  - 可与 P1/P2 并行：写入同一测试文件时实际合并编辑以避免冲突

- [x] P4. 更新 API README
  - 输入：B1-B7 已实现行为和非目标
  - 输出：auth env vars、public/protected rule、login/logout/me、CSRF header、development-only auth disabled、验证命令、明确非目标
  - 写入边界：`apps/api/README.md`
  - 可与 P1-P3 并行：不共享写入文件

### 审核检查点

- [x] R1. 确认本 change 没有引入用户注册、RBAC、多租户、OAuth、SSO、用户表、session 表或 audit persistence。
- [x] R2. 确认 production 默认不会关闭鉴权，不会默认 insecure cookie；确认当前 local Docker compose 未被文档或实现误判为 production 安全默认。
- [x] R3. 确认 public route 只包含系统探针和非业务 version route；业务 API 默认 protected。
- [x] R4. 确认 router 不直接手写 cookie 解析、capability 字符串判断或 CSRF 校验。
- [x] R5. 确认 `/me`、错误响应、日志和测试输出不泄露 session、cookie、secret、口令、hash、私有策略或 stack trace。
- [x] R6. 确认 actor/audit context 只传递脱敏 actor 与 request metadata，供后续高风险 API 复用。
- [x] R7. 确认 OpenAPI routes 使用 `ApiResponse[T]` envelope、显式 tags，并且 production OpenAPI 不暴露 debug-only paths。

## 验证任务

- [x] V1. 验证 OpenSpec change：`openspec validate add-api-cookie-session-auth --type change --strict --json`
- [x] V2. 实现阶段运行 API 测试：`cd apps/api && uv run python -m unittest discover -s src/tests`

## OpenSpec-only PR 门禁

新建或大幅更新本 change 后，必须先创建 OpenSpec-only PR。该 PR 只能包含：

- `openspec/changes/add-api-cookie-session-auth/proposal.md`
- `openspec/changes/add-api-cookie-session-auth/design.md`
- `openspec/changes/add-api-cookie-session-auth/tasks.md`
- `openspec/changes/add-api-cookie-session-auth/specs/api-cookie-session-auth/spec.md`

维护者在该 PR 下明确评论“没问题”或批准前，不允许：

- 实现代码。
- 添加依赖。
- 修改 API/Web/DB/plugin/Agent runtime。
- 将 OpenSpec artifacts 与 implementation 混在同一个 PR。

## 说明

- B0 是硬阻塞项，因为本 change 影响 API auth 行为、安全边界和跨文件契约。
- B1-B7 基本串行，因为 settings、安全默认、session、actor、capability、errors、CSRF 和 routes 共享鉴权边界。
- B6 之后测试与 README 可以并行推进；如果多个测试任务写入同一文件，实际实现时应统一编辑以避免冲突。
- 本 change 不委派子 Agent，除非用户在实现阶段明确允许并行代理工作。
