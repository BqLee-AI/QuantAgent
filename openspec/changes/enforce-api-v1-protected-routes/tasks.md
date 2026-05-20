# Tasks: API v1 public allowlist 与默认 protected 路由边界

## 状态

当前状态为 OpenSpec artifacts 已创建并获得实现认可，进入 API runtime 实现与验证阶段。

## 任务图

### 阻塞串行路径

- [x] B0. 读取 issue #92、PR #87 合入状态和现有 auth spec
  - 输入：issue #92、PR #87、`openspec/specs/api-cookie-session-auth/spec.md`、`apps/api/README.md`
  - 输出：确认 #87 已合入，#92 需要新建 active change
  - 写入边界：无

- [x] B1. 创建 OpenSpec-only artifacts
  - 输入：issue #92、#87 review 剩余边界、稳定 `api-cookie-session-auth` spec、`docs/design/08-api-and-websocket-design.md`
  - 输出：`proposal.md`、`design.md`、`tasks.md`、spec delta
  - 写入边界：`openspec/changes/enforce-api-v1-protected-routes/**`
  - 阻塞原因：本 change 影响 API auth 行为、安全边界和 route registration 契约

- [x] B2. 验证 OpenSpec change
  - 输入：B1 artifacts
  - 输出：`openspec validate enforce-api-v1-protected-routes --type change --strict --json` 通过
  - 写入边界：无
  - 依赖：B1

- [x] B3. 等待 OpenSpec-only PR 认可
  - 输入：B2 验证结果
  - 输出：维护者明确评论“没问题”或批准
  - 写入边界：GitHub PR
  - 依赖：B2

### 审核通过后的实现路径

- [x] I1. 设计并实现 API v1 route registration helper
  - 输入：B3 审核结论、当前 `register_api_v1_routes`
  - 输出：public/protected router 注册边界；protected router 统一注入 session dependency；public allowlist 单一代码声明位置；禁止新增业务 router 通过裸注册或 route-level ad hoc dependency 冒充默认 protected
  - 写入边界：`apps/api/src/quantagent/api/routers/register.py` 及必要相邻 API 私有 helper
  - 依赖：B3

- [x] I2. 迁移现有 API v1 routers 到 public/protected 分类
  - 输入：I1 helper、现有 health/version/auth/debug routers
  - 输出：health/ready/version/login 作为 public；logout/me/debug 作为 protected；debug 仍 production 不注册
  - 写入边界：`apps/api/src/quantagent/api/routers/**`
  - 依赖：I1

- [x] I3. 保持 capability 与 CSRF 细粒度 guard
  - 输入：#87 `require_capability`、`require_csrf`
  - 输出：默认 protected 不替代 capability/CSRF；logout 同时满足 session 和 CSRF；需要 capability 的测试 route 仍缺 capability 返回 403
  - 写入边界：`apps/api/src/quantagent/api/**`、`apps/api/src/tests/**`
  - 依赖：I2

- [x] I4. 补 runtime behavior 与 registration tests
  - 输入：I1-I3 实现
  - 输出：public allowlist anonymous success；login anonymous success；未显式添加 route-level auth dependency 的 protected test router anonymous 401；同 route 带 session success；logout anonymous 401；debug 非 production protected；request id envelope 校验
  - 写入边界：`apps/api/src/tests/**`
  - 依赖：I2、I3

- [x] I5. 补 OpenAPI 与 README 验证
  - 输入：I1-I4 实现
  - 输出：production OpenAPI excludes debug-only paths；route tags/envelope 不回退；README 同步 public/protected rule 和 OpenAPI security scheme 是否本轮实现
  - 写入边界：`apps/api/src/tests/**`、`apps/api/README.md`
  - 依赖：I4

### 可并行项

- I4 和 I5 可以在 I2 后并行准备测试断言，但如果写入同一测试文件，实际编辑时应合并处理以避免冲突。
- README 更新可与测试补齐并行，因为写入边界不同。
- OpenAPI cookie security scheme 如果实现成本低，可与 I5 并行；否则在 PR 说明中作为未实现增强项记录。

### 审核点

- [x] R1. 确认本 change 未新增业务 API、RBAC、多用户、OAuth、SSO、数据库 session 表或 audit persistence。
- [x] R2. 确认 public allowlist 只包含 health、ready、version 和 login。
- [x] R3. 确认 logout、me、debug 和测试业务 route 均不是 public。
- [x] R4. 确认默认 protected 只提供 session guard，不替代 capability、CSRF 或 Policy Gate。
- [x] R5. 确认 production OpenAPI 不暴露 debug-only paths。
- [x] R6. 确认 401/403 仍走统一 envelope 且携带 request id。
- [x] R7. 确认 README、OpenAPI 或 route-level dependency 没有取代 registration boundary 成为权限真源。

## 清单

- [x] 创建 `openspec/changes/enforce-api-v1-protected-routes/proposal.md`。
- [x] 创建 `openspec/changes/enforce-api-v1-protected-routes/design.md`。
- [x] 创建 `openspec/changes/enforce-api-v1-protected-routes/tasks.md`。
- [x] 创建 `openspec/changes/enforce-api-v1-protected-routes/specs/api-cookie-session-auth/spec.md`。
- [x] 运行 `openspec validate enforce-api-v1-protected-routes --type change --strict --json`。
- [x] 准备 OpenSpec-only PR，范围仅包含本 change artifacts。

## 实现护栏

- OpenSpec-only PR 审核通过前，不修改 API runtime 代码。
- 不把 OpenSpec artifacts 和 implementation 混在同一个 PR。
- 不创建 `docs/openspec`。
- 不提交 runtime 本地数据、secret、真实 `.env` 或生成缓存。
- 不把 debug route 作为 public allowlist 扩展。
- 不把 frontend 隐藏入口作为权限边界。

## 验证任务

- [x] V1. OpenSpec 验证：`openspec validate enforce-api-v1-protected-routes --type change --strict --json`
- [x] V2. 实现阶段 API 测试：`cd apps/api && uv run python -m unittest discover -s src/tests`
