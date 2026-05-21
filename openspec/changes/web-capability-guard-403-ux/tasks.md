## 1. OpenSpec And Capability Baseline

- [x] 1.1 复核 issue #106、`docs/design/09-frontend-architecture-design.md`、issue #97 与 `openspec/specs/api-cookie-session-auth/spec.md` / `openspec/specs/router-layout/spec.md` / `openspec/specs/api-client-error-governance/spec.md`，并确认 proposal / design 明确写出：本轮只收 capability policy、route guard、navigation / entry policy 与统一 403 UX，不扩展 RBAC、多用户、租户、后端 capability 来源或新鉴权服务。
- [x] 1.2 在 design 中形成首批 capability-to-route / action policy 表，至少覆盖当前 capability 集、workspace 入口和高风险 action 分类。
- [x] 1.3 完成 `web-capability-guard-403-ux` 的 OpenSpec artifacts，并运行 `openspec validate web-capability-guard-403-ux --type change --strict --json` 通过。
- [x] 1.4 在任何 `apps/web` 实现代码改动前提交 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入实现代码阶段。

## 2. Shared Capability Policy

- [x] 2.1 在 `apps/web/src/shared/auth/` 定义集中 capability policy 落点，完成条件是 route mapping、action mapping 和判断 helper 都从同一边界导出。
- [x] 2.2 明确未登录、已登录且可访问、已登录但 capability 不足三类状态的共享判断接口，完成条件是 route guard 不再把 capability 判断揉进登录跳转逻辑。
- [x] 2.3 约束页面组件不得手写 capability 字符串；完成条件是页面和布局层只消费共享 policy，而不是自行决定 navigation hiding / disabling。

## 3. Routes, Navigation And 403 UX

- [x] 3.1 为 workspace 路由定义 capability-aware guard，完成条件是 capability 不足访问不会被重定向到 `/login`，而是进入统一 forbidden route 语义。
- [x] 3.2 为主导航和首批 workspace 页面入口定义统一的 `hidden` / `disabled-with-reason` 策略，完成条件是这些状态来自共享 policy，而不是页面自行决定。
- [x] 3.3 定义统一页面级受限态，完成条件是它包含权限说明、返回入口以及 `request_id` / `trace_id` 的可见排查入口。
- [x] 3.4 定义局部高风险操作的统一 403 提示语义，完成条件是复用 shared API error 元数据，并且不泄露 session cookie、password、secret、token 或私有策略原文。
- [x] 3.5 更新 `apps/web` 说明，明确 capability policy 只负责 UX 与误操作预防，后端 capability guard 仍是真源。

## 4. Verification

- [x] 4.1 增加 unit 测试覆盖 capability policy、route / action 映射与状态判断 helper，完成条件是 capability 字符串不再需要通过页面行为间接验证。
- [x] 4.2 增加 component 或 e2e 验证，至少覆盖 capability 缺失导航表现、受限路由不跳 `/login`、403 元数据展示与敏感字段不泄露。
- [x] 4.3 在 OpenSpec 文档阶段运行 `openspec validate web-capability-guard-403-ux --type change --strict --json`，确保 change schema 通过。
- [x] 4.4 在实现代码阶段运行 `bun run --cwd apps/web test:unit`、`bun run --cwd apps/web test:ct`、`bun run --cwd apps/web test:e2e`、`bun run lint` 与 `bun run build --filter=web`，并在实现 PR 中记录未执行项与原因。
