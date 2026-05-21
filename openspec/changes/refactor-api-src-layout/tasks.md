## 1. OpenSpec 审核门槛

- [ ] 1.1 确认 issue #105、`apps/api/README.md`、`apps/api/AGENTS.md`、`docs/design/01-tech-stack-and-project-structure.md` 和 `docs/design/08-api-and-websocket-design.md` 是本 change 的输入真源。
- [ ] 1.2 运行 `openspec validate refactor-api-src-layout --type change --strict --json`，确认 proposal、design、spec 和 tasks 通过 strict 校验。
- [ ] 1.3 创建 OpenSpec-only PR，范围只包含 `openspec/changes/refactor-api-src-layout/**`。
- [ ] 1.4 等待维护者在 OpenSpec-only PR 下明确评论“没问题”或批准，再进入代码实现。

## 2. 实现前基线和迁移边界

- [ ] 2.1 在实现分支上运行 `cd apps/api && uv run python -m unittest discover -s src/tests`，记录目录重构前的 API 测试基线。
- [ ] 2.2 用 `rg "quantagent\\.api\\.(auth|middleware|responses|errors|exceptions|routers\\.register)" apps/api/src apps/api/README.md apps/api/AGENTS.md` 确认旧 import 和文档引用面。
- [ ] 2.3 基于引用面列出需要最小兼容 re-export 的高风险旧入口；只有被测试、文档、仓库内其他 app/package 或可能的外部脚本直接引用的旧模块路径才进入清单。
- [ ] 2.4 未列入高风险旧入口清单的内部引用必须迁移到新路径，不因迁移方便保留旧路径 re-export。

## 3. HTTP 传输层目录迁移

- [ ] 3.1 创建承接现有代码的 HTTP 传输层目录，并迁移响应信封、API 层错误类型、异常处理注册和 Request ID middleware。
- [ ] 3.2 更新应用工厂、异常处理、路由、数据库依赖和测试中的相关 import，使内部引用使用新 HTTP 路径。
- [ ] 3.3 确认错误响应仍使用 `code/data/msg/error` envelope，并且响应 header 与错误体中的 `request_id` 保持一致。

## 4. API 私有 Auth 模块拆分

- [ ] 4.1 将当前 Cookie Session 鉴权拆入 `auth/` 边界，按 actor/capability、session/cookie、CSRF/dependency 和 audit context 拆分职责；`refresh_session` 等活动续期逻辑归入 session/cookie 边界。
- [ ] 4.2 保持 login/logout/me、development auth bypass、production secure cookie 校验、session 签名、`/me` session refresh、capability guard 和 CSRF guard 行为不变。
- [ ] 4.3 确认 `/api/v1/me` 在 session 模式下仍刷新 HttpOnly session cookie 和 `csrf_token`，development auth bypass 下仍不签发 session cookie。
- [ ] 4.4 确认 auth 模块仍留在 `apps/api`，不下沉到 `packages/core`，不扩展为 RBAC、多用户、OAuth 或 SSO。

## 5. API v1 路由边界迁移

- [ ] 5.1 将标准 API v1 route、debug route 和 registration helper 收敛到显式 `routers/v1/` 边界。
- [ ] 5.2 保持 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 和 public/protected 分类作为 API v1 route 注册真源。
- [ ] 5.3 确认 production 环境仍不注册 debug route，非 production debug route 仍不加入 public allowlist。

## 6. 最小兼容和文档同步

- [ ] 6.1 为已确认的高风险旧入口保留薄 re-export；re-export 只转发新路径符号，不写入新逻辑。
- [ ] 6.2 更新 `apps/api/README.md` 的目录说明、新增 route 流程、auth/http/router 边界和最小验证命令。
- [ ] 6.3 更新 `apps/api/AGENTS.md` 的关键目录索引和本地规则，明确不新增空的 `services/repositories/domain/models/usecases` 等目录。
- [ ] 6.4 用 `rg "routers/register|routers/v1|http/" apps/api/README.md apps/api/AGENTS.md apps/api/src apps/api/src/tests` 检查文档和代码路径说明一致。

## 7. 验证和收口

- [ ] 7.1 运行 `cd apps/api && uv run python -m unittest discover -s src/tests`，确认 API runtime 和 OpenAPI 契约测试通过。
- [ ] 7.2 人工确认 `/api/v1/health`、`/api/v1/ready`、`/api/v1/version`、`/api/v1/auth/login`、`/api/v1/auth/logout` 和 `/api/v1/me` 未发生路径、状态码、response_model、tags 或 envelope 行为变化。
- [ ] 7.3 人工确认 public allowlist、protected-by-default、CSRF、`/me` session refresh、production secure cookie 和 debug production gating 未回归。
- [ ] 7.4 在实现 PR 说明中链接 issue #105 和 `refactor-api-src-layout` change，说明依据、改动摘要、验证结果、最小兼容入口和未验证风险。
- [ ] 7.5 确认实现 PR 不混入 OpenSpec-only 审核前新增的大幅 spec 修改；如实现发现 change 边界需要调整，先补 OpenSpec artifacts 并重新完成审核门槛。
