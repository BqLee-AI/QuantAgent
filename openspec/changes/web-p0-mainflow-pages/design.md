## Context

当前仓库已经有稳定的前端路由与登录能力：

- `router-layout` 规定了管理台壳、导航和根路径默认入口。
- `web-login-cookie-session-auth` 规定了 `/login`、受保护路由和默认首页流。

但这两层 stable spec 仍然把“默认首页流”当作抽象入口，没有把首页究竟是 Dashboard 还是 `/events` 写成稳定契约。代码现状也仍然把根路径 `/` 导向 `/events`，与 issue #127 和当前页面 PRD 已确认的主链路不一致。

本 change 不是重写页面 PRD，而是把已经确认的 P0 主链路结论收成稳定契约，并纠正现有 stable 路由语义。

## Goals / Non-Goals

**Goals:**

- 固化 P0 主链路的四个核心页面职责：Dashboard、Events、Event Detail / Decision、Approvals。
- 明确四个页面的主对象、主任务和禁止职责。
- 把根路径 `/` 的默认首页语义从 `/events` 收口为 Dashboard。
- 为 #129、#130、#131 提供一个可复用的统一上游 change。
- 让后续实现者能够在不重新做产品判断的情况下进入页面实现。

**Non-Goals:**

- 不在本 change 中实现 React 页面、路由代码、API contract 或组件样式。
- 不重新设计 Runtime、Plugins、Models、Settings 等非 P0 页面。
- 不把“相关历史事件”“真实执行流程”“首页外独立系统健康页”拉进 V1 主链路。
- 不修改登录、会话、CSRF 或 capability guard 的既有行为契约，除非它们与默认首页入口直接相关。

## Decisions

### 1. 用新的页面 capability 承接 P0 主链路，而不是继续堆进 `router-layout`

`router-layout` 适合承载“路由壳、导航、默认入口”这类稳定布局语义，但不适合同时承载每个业务页面的主对象、页面任务和非目标。把所有页面边界都继续塞进 `router-layout`，会让该 spec 演变成混合路由、布局和产品信息架构的大杂烩。

因此本 change 采用两层处理：

- `router-layout` 只修改根路径默认入口这一条稳定路由语义。
- 新增 `web-p0-mainflow-pages` 能力，专门定义 Dashboard、Events、Event Detail / Decision、Approvals 的行为边界。

这样后续页面实现 issue 可以直接引用页面能力 spec，而不必从布局 spec 中拆意图。

### 2. Dashboard 必须是独立默认首页，而不是 `/events` 的别名或重皮肤

这是 issue #127 的核心决策。Dashboard 需要同时容纳高价值事件、待审批摘要和关键健康提醒，承担“今天先看什么、接下来处理什么、系统是否影响判断质量”的总控职责。`/events` 只负责浏览、筛选和扩展事件视野。

替代方案是继续让 `/events` 兼任总首页。该方案会把事件列表、筛选工具条和首页总控职责混在一起，使 Dashboard 的独立价值消失，也会让 #129、#130、#131 对首页入口产生不同假设，因此不采用。

### 3. `/events` 不是首页，因为它解决的是“浏览更多事件”，不是“给出第一判断”

`/events` 的主任务是让用户在 Dashboard 之外浏览、筛选和扩展重点事件视野。它回答的是“还有哪些事件值得看”“如何收窄事件集合”，而不是“今天第一眼先看什么、有哪些审批待处理、系统是否影响判断质量”。

如果让 `/events` 继续承担首页职责，事件中心就会被迫同时容纳首页总控摘要、事件筛选工具和后续详情入口，最终既不像首页，也不像事件中心。因此本 change 将 `/events` 固定为从 Dashboard 进入的事件中心，而不是默认首页。

### 4. 页面边界用“主对象 + 主任务 + 禁止职责”定义，而不是枚举最终组件

仅靠“页面名称和路由”不足以避免后续实现漂移。本 change 以三件套固定页面边界：

- 主对象：页面围绕什么资源组织。
- 主任务：用户进入该页首先要完成什么判断。
- 禁止职责：明确哪些动作或信息不应出现在该页。

例如：

- Dashboard：主对象聚焦高价值事件；禁止承担审批执行和插件治理。
- Events：主对象是事件集合；禁止承担首页总控和审批动作。
- Event Detail：主对象是单条事件；禁止直接批准或执行高风险动作。
- Approvals：主对象是 ApprovalRequest；禁止把批准语义写成真实执行完成。

这种定义方式与现有页面 PRD 的结构一致，也更适合转成验收场景。相反，如果在 OpenSpec 中枚举最终组件名、字段和布局细节，会抢掉 #129、#130、#131 的实现设计空间，并让 spec 过早绑定尚未稳定的 API contract，因此不采用。

### 5. 把 V1 非目标写进 spec，而不是只留在 issue 或 PRD 文字里

`issue #127` 评论已经明确“相关历史事件不进入 V1 主链路”，但现有页面 PRD 和代码骨架之外还没有一个稳定契约来约束后续实现。如果只把这个结论放在 issue 里，后续 Web issue 很容易重新把它带回来。

因此本 change 直接将以下边界写入 spec：

- Dashboard 不拆独立系统健康页面，只展示影响判断质量的关键提醒。
- Event Detail 不把相关历史事件作为 P0 必须展示内容。
- P0 主链路不引入真实执行流程、插件治理入口或完整运行时排障台。

### 6. `router-layout` 只改默认入口，不重复登录和受限访问契约

本 change 需要修改 `router-layout` 中根路径 `/` 的默认入口，但不应把 `/login`、受保护路由、capability-limited forbidden 等行为重新定义一遍。这些行为已经由 `web-login-cookie-session-auth` 和后续 capability guard 类 spec 负责。

替代方案是在本 change 的 `router-layout` delta 中同时复制登录恢复、403 和 capability snapshot 语义。该方案会让归档后的 `router-layout` 变成认证和权限真源，造成职责重叠，因此不采用。

### 7. PRD 回链单独处理，不在 OpenSpec-only PR 中混入页面附录改动

当前 `origin/main` 上的页面 PRD 已经基本符合 `issue #127` 结论。再次大规模重写 PRD 只会扩大本轮范围，并增加 OpenSpec-only PR 的噪音。

因此本轮保持 OpenSpec-only 边界：

- 本 change 只提交 `proposal.md`、`design.md`、`tasks.md`、`specs/**/spec.md` 和必要元数据。
- `docs/prd/08-frontend-pages-overview.md` 对 `web-p0-mainflow-pages` 的回链在后续独立文档变更中处理，不与 OpenSpec-only PR 混提。
- 不大改 `00-dashboard.md`、`02-events-home.md`、`03-event-detail.md`、`04-approvals-index.md`，除非后续实现或评审发现与 stable spec 直接冲突的语句。

## Risks / Trade-offs

- [Risk] 只修改 OpenSpec 而不立刻改路由代码，短期内仓库实现仍然保持 `/ -> /events`。
  -> Mitigation：在 tasks 中明确实现 PR 必须先处理默认首页入口，再进入 Dashboard UI 或详情/审批页面实现。

- [Risk] 新增 `web-p0-mainflow-pages` capability 后，reviewer 可能质疑和现有页面 PRD 的边界重复，或认为 OpenSpec-only PR 混入了页面附录改动。
  -> Mitigation：proposal 和 design 中明确 PRD 是页面附录，OpenSpec 是行为真源；PRD 回链单独处理，不在本 PR 混入。

- [Risk] 事件详情页当前 PRD 提到了更多信息块，spec 若写得过细会抢掉 #130 的设计空间。
  -> Mitigation：spec 只固定主阅读顺序、关键入口和 P0 非目标，不发明最终字段 contract 或交互细节。

- [Risk] 修改 `router-layout` 默认入口会与 `web-login-cookie-session-auth` 的“默认首页流”表述形成歧义。
  -> Mitigation：在 `router-layout` 中显式把默认首页流指向 Dashboard；登录 spec 继续保留“进入默认首页流”的抽象，不重复写死路由细节。
