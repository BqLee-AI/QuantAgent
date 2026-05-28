## 1. 主链路契约与实现收口

- [x] 1.1 完成 `proposal.md`、`design.md`、`tasks.md`、`specs/web-p0-mainflow-pages/spec.md` 和 `specs/router-layout/spec.md`。
- [x] 1.2 核对 proposal 的 capabilities 与 specs 目录一一对应，且 `router-layout` delta 只修改默认首页入口语义。
- [x] 1.3 在同一 PR 中同步落地 `apps/web` 页面骨架、默认首页入口和主链路路由，不让 OpenSpec 与实现继续分叉。
- [x] 1.4 更新 PR 说明，明确当前 PR 同时交付页面契约与 Dashboard / Events / Approval 主链路骨架。
- [x] 1.5 收敛 `docs/prd/08-frontend-pages-overview.md` 的 OpenSpec 建议范围，只保留当前 change 已实际承接的页面契约边界。
- [ ] 1.6 后续若拆出独立文档或 OpenSpec-only 流程，需在新的 change / PR 中单独说明边界，不回写当前实现型 PR 的完成状态。

## 2. 后续实现输入

- [ ] 2.1 将 `apps/web` 根路径默认入口从 `/events` 调整为独立 Dashboard 首页流。
- [ ] 2.2 为 Dashboard 增加受保护工作区入口，并更新导航、面包屑与默认入口策略。
- [ ] 2.3 保持 `/login`、受保护路由和 capability-limited forbidden 语义与既有登录和权限 spec 一致。
- [ ] 2.4 issue #129 的实现必须以 Dashboard 为独立默认首页，并保持首页只承接重点事件、待审批摘要、关键健康提醒和主工作入口。
- [ ] 2.5 issue #130 的实现必须保持 `/events` 只承担事件中心职责，并让 `/events/:eventId` 首屏优先展示行业影响分析与最佳动作。
- [ ] 2.6 issue #131 的实现必须保持 `/approvals` 为独立人类确认工作台，并严格区分“批准”与“真实执行完成”。

## 3. 验证

- [x] 3.1 运行 `openspec validate web-p0-mainflow-pages --type change --strict --json`。
- [x] 3.2 人工核对 OpenSpec artifacts、PRD 真源映射和 `apps/web` 页面骨架已经同步到同一主链路语义。
- [x] 3.3 人工核对 issue #129、#130、#131 可直接回链到本 change，而不再各自假设不同首页入口。
- [x] 3.4 收敛 `docs/prd/08-frontend-pages-overview.md` 的 OpenSpec 真源映射，只保留 Dashboard、Events、Event Detail、Approvals 和 `/` 默认入口语义。
- [x] 3.5 运行 `cd apps/web && bun run build`，确认当前页面骨架、路由和导航收口可以正常构建。
