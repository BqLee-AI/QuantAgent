## Why

QuantAgent Web 的 P0 页面 PRD 已经收口出一条明确的操盘主链路，但当前 stable OpenSpec 仍停留在“有这些路由和管理台壳”的层面，没有把 `/`、`/events`、`/events/:eventId`、`/approvals` 的职责差异固化成统一契约。继续让后续 issue 各自实现，会把首页角色、事件详情焦点和审批入口边界重新打散。

Issue #127 以及其评论已经明确三个产品结论：根路径必须保留独立 Dashboard、系统健康提醒先作为 Dashboard 模块存在、V1 主链路不纳入相关历史事件展示。本 change 只固化这些页面契约，作为 #129、#130、#131 的统一上游真源。

## What Changes

- 新增 `web-p0-mainflow-pages` capability，定义 Dashboard、`/events`、`/events/:eventId`、`/approvals` 的页面契约。
- 修改 `router-layout` capability，只调整根路径 `/` 的默认首页语义：从直接进入 `/events` 收口为进入独立 Dashboard 首页流。
- 固化 Dashboard 首版边界：只承接重点事件、待审批摘要、关键健康提醒和主工作入口。
- 固化 `/events` 边界：承接事件浏览、筛选和扩展重点事件视野，不承担系统总首页职责。
- 固化 `/events/:eventId` 边界：围绕单条事件组织事实、行业影响分析、最佳动作和审批入口。
- 固化 `/approvals` 边界：集中处理 ApprovalRequest，并严格区分“批准”与“真实执行完成”。
- 将“V1 不纳入相关历史事件展示”“系统健康提醒不拆独立首页外治理页”等范围写入页面行为契约。

## Capabilities

### New Capabilities
- `web-p0-mainflow-pages`: 定义 QuantAgent Web P0 主链路页面的职责边界、默认阅读顺序、入口出口和首版非目标。

### Modified Capabilities
- `router-layout`: 根路径 `/` 的默认入口从事件中心收口为独立 Dashboard 首页流。

## Impact

- OpenSpec stable spec：后续归档会新增 `web-p0-mainflow-pages`，并更新 `router-layout` 的根路径默认入口语义。
- Web 实现输入：后续实现阶段需要调整 `apps/web` 的根路由、Dashboard 入口、导航/面包屑和默认入口策略。
- PRD 对齐：`docs/prd/08-frontend-pages-overview.md` 需要在独立文档变更中回链本 change，避免 PRD 与 OpenSpec 分叉，同时保持本 PR 为 OpenSpec-only 边界。
- 下游 issue：#129、#130、#131 需以本 change 作为统一上游，不再各自发明首页和主链路边界。
- 非影响范围：本 change 不实现 React 页面、API contract、generated client、数据模型或真实审批执行链路。
