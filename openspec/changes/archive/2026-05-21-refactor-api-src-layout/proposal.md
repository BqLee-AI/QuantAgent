## Why

issue #105 要求在不改变外部行为的前提下，重构 `apps/api` 当前扁平的源码目录结构。`apps/api` 已经包含 API v1 骨架、响应信封、异常处理、Request ID、数据库 readiness、路由注册和本地 Cookie Session 鉴权，如果继续把这些能力放在 `quantagent.api` 根下增长，后续新增 route、鉴权保护或调试入口时容易混淆 HTTP 传输层、API 私有鉴权和可复用领域逻辑边界。

现在需要先用 OpenSpec 固化目录边界、兼容策略、文档同步和验证要求，避免直接做代码重构时把实现判断留在聊天或 PR 描述里。

## What Changes

- 将 HTTP 传输层基础能力收敛到明确目录，例如 `http/`，承接响应信封、API 层错误类型、异常处理和 Request ID middleware。
- 将当前 API 私有 Cookie Session 鉴权从单文件拆成明确的 `auth/` 模块，区分 actor/capability、session/cookie、CSRF/dependency 和 audit context，并保留 `/me` 基于 `refresh_session` 的活动续期行为。
- 将标准 API v1 route 和注册真源收敛到显式 v1 路由边界，例如 `routers/v1/`。
- 采用最小兼容 import 策略：内部引用迁移到新路径，只对高风险公共入口保留薄 re-export，不把旧路径作为新增代码入口。
- 同步更新 `apps/api/README.md` 和 `apps/api/AGENTS.md`，使目录索引、route 注册说明和长期边界规则与实际结构一致。
- 保持现有 route 路径、OpenAPI 契约、`code/data/msg/error` envelope、public/protected allowlist、debug production gating、数据库 readiness、Cookie Session、`/me` session refresh 和 CSRF 行为不变。

## Capabilities

### New Capabilities

- `api-src-layout`: 定义 `apps/api` 源码目录分层、迁移兼容策略和行为不变的目录重构验收口径。

### Modified Capabilities

- 无。本 change 不修改 `api-cookie-session-auth` 的 requirement，只引用该 stable spec 和当前 API 测试作为 Cookie Session、`/me` session refresh、capability guard、CSRF guard、session cookie 和 development bypass 行为不变的约束。

## Impact

- `apps/api/src/quantagent/api/**`：目录结构、模块 import 和 API 私有边界会在后续实现 PR 中调整。
- `apps/api/src/tests/**`：测试 import 需要随新目录迁移，并继续覆盖 runtime 行为和 OpenAPI 契约。
- `apps/api/README.md`、`apps/api/AGENTS.md`：目录索引、新增 route 流程、auth/http/router 边界和最小验证说明需要同步更新。
- `docs/design/01-tech-stack-and-project-structure.md`、`docs/design/08-api-and-websocket-design.md`：作为本 change 的设计依据；本轮不修改这些长期设计文档。
- 不新增依赖，不新增业务 API，不调整 Docker、数据库迁移、前端契约生成或 package 边界。
