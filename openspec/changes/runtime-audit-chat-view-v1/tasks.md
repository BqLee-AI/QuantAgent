## 1. OpenSpec 审核门槛

- [x] 1.1 提交 OpenSpec-only PR，只包含 `runtime-audit-chat-view-v1` 的 proposal、design、tasks、specs 和必要说明。（本轮由用户在对话中确认“可以，开始实现”，不单独等待 OpenSpec-only PR）
- [x] 1.2 在 PR 说明中链接 #270 和 PR #257，说明本 change 只定义 `/runtime` 审计聊天流，不实现页面代码、不合并 #257。（后续实现 PR 说明需补证据链）
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。（用户已在本轮明确批准进入实现）

## 2. PR #257 处理决策

- [x] 2.1 审核 PR #257 的写入范围，列出可复用的 Runtime Inspect contracts、queries、error state、partial unavailable 和脱敏字段。
- [x] 2.2 列出必须替换或重做的页面层：多面板首屏、四类资源表格首屏、长说明式占位内容。
- [x] 2.3 在后续实现 PR 中说明 #257 是继续改造、部分 cherry-pick、关闭替代，还是拆分后另开 PR。

## 3. Runtime audit chat 页面模型

- [x] 3.1 定义 `RuntimeAuditMessage`、`RuntimeAuditMessageGroup`、filter params、safe detail 和 related refs 的 TypeScript 类型。
- [x] 3.2 定义 Router Agent fixture 或 read model mapper，覆盖 route、discard、review、degraded RSS-summary-only、schema validation failure。
- [x] 3.3 定义 audit message 的 stage、actor、status、decision、badge 和 evidence refs 显示规则。
- [x] 3.4 定义 compact health/status strip 的边界：只做状态提醒，不作为首屏主体。

## 4. 前端分层落点

- [x] 4.1 route 仅保留 `createFileRoute`、search params 和 `<RuntimeAuditPage />` 挂载。
- [x] 4.2 在 `features/runtime/api/` 放置 runtime audit contracts / API；如使用 fixture，不伪造生产 endpoint。
- [x] 4.3 在 `features/runtime/queries/` 放置 query keys 和 query hooks，通过 runtime `apis` 访问业务 API。
- [x] 4.4 在 `features/runtime/hooks/` 放置 `useRuntimeAuditPage`、filters、selection 和 refresh 编排。
- [x] 4.5 在 `features/runtime/components/` 拆分 page、filter bar、conversation、message、detail drawer、trace panel 和 states。
- [x] 4.6 在 `features/runtime/utils/` 放置格式化、脱敏和 fixture 转换纯函数。
- [x] 4.7 更新 `features/runtime/README.md`，写清职责、入口、不负责什么、以及 raw payload 禁止展示规则。

## 5. 安全、状态与失败路径

- [x] 5.1 实现或定义 safe details 脱敏规则，禁止 raw prompt、CoT、provider raw response、secret、ORM object、plugin instance 和未脱敏 payload。
- [x] 5.2 覆盖 loading、empty、permission denied、partial unavailable、provider/model failure、schema validation failure、degraded input。
- [x] 5.3 对非显然安全边界写中文注释，说明为什么详情抽屉不能直接展示 raw payload。
- [x] 5.4 确保 `discard`、`review`、`route` 在 UI 上是不同状态，不互相伪装。

## 6. 验证

- [x] 6.1 运行 `openspec validate runtime-audit-chat-view-v1 --type change --strict --json`。
- [x] 6.2 后续实现 PR 至少运行 `bun run --cwd apps/web test:unit -- runtime-audit` 或等价单测，覆盖格式化、脱敏、filter params 和 Router Agent fixture。
- [x] 6.3 后续实现 PR 至少运行 `bun run --cwd apps/web lint`。
- [x] 6.4 如果 route、runtime factory 或 build-sensitive 类型发生变化，运行 `bun run --cwd apps/web build`，若 main 上存在既有阻断需在 PR 说明中写清。
- [x] 6.5 人工验收 `/runtime` 首屏不再是四张技术资源表格，并能用 Router Agent fixture 区分 route、discard、review、degraded 和 schema invalid。
