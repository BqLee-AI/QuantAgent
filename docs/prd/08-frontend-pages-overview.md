# 08. 前端页面规划总览

## 文档状态

**版本**：v1.0  
**状态**：页面级 PRD 基线稿  
**适用范围**：`apps/web` 管理台页面信息架构、页面职责、页面关系、模块映射与原型输入  
**基于真源**：`docs/prd/01-07`、`docs/design/09-frontend-architecture-design.md`、当前 `apps/web` 路由骨架、GitHub issue `#127-#132`

## 为什么补这一层

当前 PRD 已经回答了产品是什么、为什么存在、有哪些模块边界，但还没有把“前端每个页面具体解决什么问题、页面里要放哪些模块、每个模块承担什么职责”系统地沉淀下来。

这一层文档的目的不是替代设计稿，而是把以下内容固定下来：

- 哪些页面是一阶段必须做的。
- 每个页面的主对象是什么。
- 每个页面最少要展示哪些信息和动作。
- 页面之间如何跳转。
- 推荐拆成哪些前端模块，避免页面开发时重新发明结构。

## 页面设计总原则

- 前端首先是**事件驱动分析工作台**，其次才是运行时管理台。
- V1 不做完整交易终端，不提供手工下单工作流。
- 事件是主对象，分析、审批、审计围绕事件展开。
- 高风险动作不在列表页直接执行，必须进入审批链路。
- REST 快照是状态真源，实时消息只做刷新与提醒。
- 前端展示结构化分析，不展示完整模型推理链。
- 所有涉及建议、审批、密钥、执行边界的页面都必须考虑审计和脱敏。

## 页面地图

| 页面 | 路由 | 页面角色 | 阶段优先级 | 主对象 |
| --- | --- | --- | --- | --- |
| Dashboard 首页 | `/` | 总控首页、重点事件与系统提醒入口 | P0 | 仪表盘 / 高价值事件 |
| 登录页 | `/login` | 进入系统、建立会话 | P0 | 会话 |
| 高价值事件首页 | `/events` | 发现重点事件、进入分析 | P0 | 事件 |
| 事件详情 / 决策页 | `/events/:eventId` | 查看事件事实、行业影响、最佳动作 | P0 | 事件 |
| 审批工作台 | `/approvals` | 集中处理待确认建议 | P0 | 审批请求 |
| 事件级审计时间线 | `/events/:eventId/audit` | 回放建议变化与人工动作 | P1 | 事件 |
| 审批详情页 | `/approvals/:approvalId` | 审批单独处理、查看完整证据 | P1 | 审批请求 |
| 一次性授权页 | `/approval-link/:token` | 外部短链审批 | P1 | 审批请求 |
| 运行看板 | `/runtime` | 看系统运行、Agent、工具和错误 | P1 | 运行态 |
| Agent Run 详情 | `/runtime/agents/:runId` | 看分析过程摘要 | P1 | Agent Run |
| Tool Invocation 详情 | `/runtime/tools/:invocationId` | 看工具调用过程 | P1 | Tool Invocation |
| 插件管理页 | `/plugins` | 看插件状态、筛选和进入配置 | P1 | 插件 |
| 插件详情页 | `/plugins/:pluginId` | 插件配置、依赖、错误、审计 | P1 | 插件 |
| Skills 页 | `/skills` | 看 Skill Registry 摘要 | P2 | Skill |
| Tools 页 | `/tools` | 看 Tool Registry 摘要 | P2 | Tool |
| Industries 页 | `/industries` | 看行业包摘要和市场映射 | P2 | Industry Package |
| 设置页 | `/settings` | 管理会话、通知、偏好、风险开关 | P2 | 系统设置 |

## 页面关系图

```text
登录
  -> Dashboard 首页
      -> 高价值事件首页
      -> 事件详情 / 决策页
          -> 审批工作台
          -> 事件级审计时间线
          -> 审批详情页
          -> 运行看板 / Agent Run 详情
          -> 插件页 / 行业包页（支撑查看）
      -> 系统健康提醒

审批工作台
  -> 审批详情页
  -> 回跳事件详情 / 决策页
  -> 事件级审计时间线

运行看板
  -> Agent Run 详情
  -> Tool Invocation 详情

插件管理页
  -> 插件详情页
```

## 页面分层

### P0：操盘主链路页面

- Dashboard 首页
- 登录页
- 高价值事件首页
- 事件详情 / 决策页
- 审批工作台

这组页面直接承接：

`Dashboard -> 发现事件 -> 理解影响 -> 看到建议 -> 人工确认`

### P1：解释性和治理型页面

- 事件级审计时间线
- 审批详情页
- 一次性授权页
- 运行看板
- Agent Run 详情
- Tool Invocation 详情
- 插件管理页
- 插件详情页

这组页面的目标不是创造新建议，而是解释系统是怎么得到建议、系统当前是否健康、插件是否可用。

### P2：索引与设置型页面

- Skills 页
- Tools 页
- Industries 页
- 设置页

这组页面用于建立后台治理能力，不应该抢占首页或详情页的注意力。

## 页面和前端模块映射原则

### 路由层

- `routes/` 只负责 URL、loader、页面入口和顶层布局组合。
- 列表页的筛选条件应稳定进入 URL search params。
- 详情页必须支持通过稳定 ID 直接打开。

### Feature 层

建议沿用 `features/<domain>/components` 进行模块拆分：

| 页面 | 推荐 feature |
| --- | --- |
| `/events`、`/events/:eventId` | `features/events` |
| `/approvals`、`/approvals/:approvalId`、`/approval-link/:token` | `features/approvals` |
| `/runtime`、`/runtime/agents/:runId`、`/runtime/tools/:invocationId` | `features/runtime` |
| `/plugins`、`/plugins/:pluginId` | `features/plugins` |
| `/skills` | `features/skills` |
| `/tools` | `features/tools` |
| `/industries` | `features/industries` |
| `/settings` | `features/settings` |

### Shared 层

建议把以下能力沉到底层共享模块：

- `shared/api`：API client、错误对象、请求上下文。
- `shared/realtime`：WebSocket 订阅与重连提醒。
- `shared/forms`：常规表单与 schema-driven form 支撑。
- `shared/ui`：页面头、统计卡、状态徽章、表格、时间线、空态、错误态。
- `shared/auth`：会话、能力可见性、退出登录。

## 一阶段建议输出顺序

1. 先定 P0 页面结构。
2. 再补审计、审批详情、运行看板、插件详情等解释型页面。
3. 最后补 Skills / Tools / Industries / Settings 这些治理型页面。

## 示例主链路

```text
09:02 操盘者登录
  -> Dashboard 看到今日重点事件区第 1 条：
     “路透：OPEC+ 将临时减产讨论提前”

09:03 用户打开事件详情
  -> 左侧看到来源、时间、事件摘要
  -> 右侧看到：
     - 影响行业：原油、油服、航运
     - 影响标的：Brent front-month, XLE
     - 风险点：消息尚未有官方公告二次确认
     - 最佳动作：观察性做多近月原油，可靠度 78/100

09:04 用户决定需要审批
  -> 进入审批工作台
  -> 在审批页查看建议动作、风险和关键证据
  -> 执行 approve 或 request_reanalysis
```

## 对应详细页面文档

- [页面文档索引](pages/README.md)
- [Dashboard 首页](pages/00-dashboard.md)
- [登录页](pages/01-login.md)
- [高价值事件首页](pages/02-events-home.md)
- [事件详情 / 决策页](pages/03-event-detail.md)
- [审批工作台](pages/04-approvals-index.md)
- [事件级审计时间线](pages/16-event-audit-timeline.md)
- [审批详情页](pages/05-approval-detail.md)
- [一次性授权页](pages/06-approval-link.md)
- [运行看板](pages/07-runtime-dashboard.md)
- [Agent Run 详情](pages/08-runtime-agent-run-detail.md)
- [Tool Invocation 详情](pages/09-runtime-tool-detail.md)
- [插件管理页](pages/10-plugins-index.md)
- [插件详情页](pages/11-plugin-detail.md)
- [Skills 页](pages/12-skills.md)
- [Tools 页](pages/13-tools.md)
- [Industries 页](pages/14-industries.md)
- [设置页](pages/15-settings.md)

## HTML 原型

可预览原型文件：

- [前端页面原型 HTML](prototypes/frontend-pages-v1.html)

该原型优先覆盖 P0 主链路和部分 P1 页面，用于快速看页面层级与信息密度，不替代正式前端实现。
