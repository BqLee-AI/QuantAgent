# Events Feature

`features/events` 负责 `/events`、`/events/all`、`/events/:eventId` 和 `/events/:eventId/audit` 的真实业务事件入口。

## 职责

- 只展示已经经过 Router Agent 处理并形成 routed read model 的新闻事件。
- 通过 `/api/v1/events` 读取业务 read model，不把 `source.event.captured`、`industry.analysis.requested` 或 `event.routed` topic 当成列表主对象。
- 列表默认展示 `decision=route|review`，`discard` 只通过显式筛选查看。
- 筛选栏只展示真实 API 支持的全局维度：关键词、行业包、路由结果、路由时间和排序。
- 行业包筛选来自 Registry 中已安装的 `industry` 插件，不在前端硬编码半导体子主题。
- 默认排序是 `routed_at_desc`，表示系统最新路由优先；可切换到 `published_at_desc` 查看新闻发布时间优先。
- 路由时间预设使用滚动窗口：`3h`、`24h`、`3d`、`7d`、`All`；后端同时支持 `time_from` / `time_to`，后续自定义时间区间控件可直接传这两个参数。
- 详情展示新闻摘要、Router Agent stage、关键字段、timeline、trace refs 和安全详情。

## 子目录

- `api/`: `EventsApi` 和后端 contract types。
- `queries/`: TanStack Query key 与查询 hook。
- `hooks/`: 页面级筛选、列表和详情编排。
- `components/`: 页面、列表、详情和状态组件。
- `types/`: 本 feature 的展示和 API 类型。
- `utils/`: label、tone、日期等纯格式化 helper。

## 不负责

- 不展示未被 Router Agent 处理的 RawEvent；这些 pending/unavailable 状态属于 `/runtime`。
- 不触发 scheduler、worker、AI 重放或 RawEvent 正文抓取。
- 不执行审批、交易或行业 MainAgent 深度分析。
- 不在 MainAgent read model 接入前提供“分析中 / 已完成分析”筛选；缺少真实状态时只在卡片或详情中显示待行业分析。
- 不使用旧评分演示 mock、旧审计 mock 或运行态 fixture 作为生产数据源。
- 不展示完整正文、raw payload、provider raw response、prompt、CoT、secret 或 ORM object。
