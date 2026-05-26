## 1. OpenSpec-only 交付

- [x] 1.1 完成 `proposal.md`、`design.md`、`tasks.md`、`specs/web-p0-mainflow-pages/spec.md` 和 `specs/router-layout/spec.md`。
- [x] 1.2 核对 proposal 的 capabilities 与 specs 目录一一对应，且 `router-layout` delta 只修改默认首页入口语义。
- [x] 1.3 核对 `docs/prd/08-frontend-pages-overview.md` 已指向 `web-p0-mainflow-pages`，避免 PRD 与 OpenSpec 分叉。
- [ ] 1.4 提交 OpenSpec-only PR，只包含本 change artifacts 与必要 PRD 对齐，不混入 React 页面、API contract、依赖升级或格式化。
- [ ] 1.5 在 PR 说明中写清楚：本 PR 固化 P0 主链路页面边界，不实现代码；审核通过后 #129、#130、#131 复用本 change。
- [ ] 1.6 等维护者在 OpenSpec-only PR 下明确评论“没问题”或批准后，再进入实现类 issue。

## 2. 后续实现输入

- [ ] 2.1 将 `apps/web` 根路径默认入口从 `/events` 调整为独立 Dashboard 首页流。
- [ ] 2.2 为 Dashboard 增加受保护工作区入口，并更新导航、面包屑与默认入口策略。
- [ ] 2.3 保持 `/login`、受保护路由和 capability-limited forbidden 语义与既有登录和权限 spec 一致。
- [ ] 2.4 issue #129 的实现必须以 Dashboard 为独立默认首页，并保持首页只承接重点事件、待审批摘要、关键健康提醒和主工作入口。
- [ ] 2.5 issue #130 的实现必须保持 `/events` 只承担事件中心职责，并让 `/events/:eventId` 首屏优先展示行业影响分析与最佳动作。
- [ ] 2.6 issue #131 的实现必须保持 `/approvals` 为独立人类确认工作台，并严格区分“批准”与“真实执行完成”。

## 3. 验证

- [x] 3.1 运行 `openspec validate web-p0-mainflow-pages --type change --strict --json`。
- [x] 3.2 人工核对 `docs/prd/08-frontend-pages-overview.md` 与本 change 的页面边界没有分叉。
- [x] 3.3 人工核对 issue #129、#130、#131 可直接回链到本 change，而不再各自假设不同首页入口。
- [ ] 3.4 在最终说明中列出未执行的代码验证，并说明原因是本轮仅交付 OpenSpec 文档。
