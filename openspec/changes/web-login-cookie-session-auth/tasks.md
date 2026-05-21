## 1. OpenSpec And Contract Baseline

- [x] 1.1 复核 issue #97、`openspec/specs/api-cookie-session-auth/spec.md`、`openspec/specs/api-client-error-governance/spec.md`、`openspec/specs/router-layout/spec.md`、`docs/design/09-frontend-architecture-design.md` 与 `apps/web/AGENTS.md`，确认本轮只交付前端登录入口、Cookie Session bootstrap、受保护路由、logout、CSRF 注入、401/403 收口和 development bypass。
- [x] 1.2 确认本轮前端契约严格消费 `POST /api/v1/auth/login`、`GET /api/v1/me`、`POST /api/v1/auth/logout`，并以 HttpOnly session cookie + `csrf_token` 为 bootstrap 边界，不扩展注册、RBAC、OAuth、SSO 或业务页面数据接入。
- [x] 1.3 完成 `web-login-cookie-session-auth` 的 OpenSpec artifacts，并通过 `openspec validate web-login-cookie-session-auth --type change --strict --json`。
- [x] 1.4 在任何 `apps/web` 实现代码改动前提交 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入代码实现。

## 2. Shared API And Auth State

- [x] 2.1 审查 `apps/web/src/shared/api/**` 当前 Bearer token 注入、401 refresh 和 `onUnauthorized` 语义，产出“哪些逻辑要移除、哪些扩展点仅保留但不作为主路径”的实现清单。
- [x] 2.2 为前端新增统一 auth bootstrap 模块或 provider，集中维护 `actor_id`、`actor_type`、`capabilities`、`csrf_token`、bootstrapping、authenticated 和 unauthorized 状态，并明确这些状态不得持久化敏感值。
- [x] 2.3 调整 shared API client，使其保持 `withCredentials=true`，并通过统一入口为 logout 和受保护写请求注入 `X-CSRF-Token`；页面组件不得手写该 header。
- [x] 2.4 统一 401 与 403 行为：401 触发集中 unauthorized 收口与状态清理，403 保持“权限不足”语义，不伪装成普通网络错误。
- [x] 2.5 审查 `apps/web/src/shared/config/**` 的 `authEnabled` 读取路径，确保 development bypass 只通过共享 runtime config 入口判断，而不是组件自行解释环境变量。

## 3. Routes And UI Entry

- [x] 3.1 在 `apps/web/src/routes/` 新增独立 `/login` 路由与最小登录表单，调用 `POST /api/v1/auth/login`，并确保登录页在 dashboard shell 外渲染。
- [x] 3.2 在 `apps/web/src/app/` 与路由入口中增加统一 guard：未登录访问受保护管理台路由时跳转 `/login`，登录成功后恢复原目标路由，直接访问 `/login` 成功后走默认首页流。
- [x] 3.3 调整应用启动 bootstrap，使首次加载和刷新统一通过 `GET /api/v1/me` 恢复会话，不在页面组件各自发 bootstrap 请求。
- [x] 3.4 支持 development bypass，但仅在 `authEnabled=false` 且 `/me` 返回 development actor 时进入管理台；UI 必须提供明显的 development/auth-disabled 提示。
- [x] 3.5 增加统一 logout action，使用当前 `X-CSRF-Token` 调用 `POST /api/v1/auth/logout`，成功后清理前端 auth bootstrap 状态并回到登录入口。
- [x] 3.6 capability 初版只展示状态，不对现有主导航做强制裁剪，并在实现说明中明确后端 capability guard 仍是权限真源。

## 4. Tests And Docs

- [x] 4.1 增加 unit / component / e2e 或 route mock 测试，至少覆盖登录成功、登录失败、刷新后 `/me` 恢复、未登录访问受保护页面、logout 和 401 失效场景。
- [x] 4.2 增加 403 与 development bypass 的最小验证，确认权限不足语义、`authEnabled=false` 判断条件与开发态提示清晰稳定。
- [x] 4.3 增加对敏感值边界的验证，确认 localStorage、sessionStorage、共享状态和日志路径中不保存 session cookie、cookie value、password、password hash、signing secret、真实 token 或私有策略。
- [x] 4.4 更新 `apps/web` 相关说明，记录本地登录、development bypass、后端 auth 契约依赖和验证入口。
- [x] 4.5 运行 `bun run --cwd apps/web test:unit`、`bun run --cwd apps/web test:ct`、`bun run --cwd apps/web test:e2e`、`bun run --cwd apps/web build`、`bun run lint` 与 `openspec validate web-login-cookie-session-auth --type change --strict --json`，并在 PR 说明中记录未执行项及原因。
