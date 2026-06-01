## runtime feature

负责 `/runtime` Runtime Dashboard V1 的只读运行态观察面。

入口：

- route: `src/routes/_app/(workspace)/runtime/index.tsx`
- page: `components/page/RuntimeDashboardPage.tsx`
- page hook: `hooks/useRuntimeDashboardPage.ts`

当前职责：

- `api/`: Runtime Inspect V1 REST contracts 与 endpoint 封装
- `queries/`: query keys 与 `useQuery` 读取逻辑
- `hooks/`: 页面级过滤、刷新和 partial unavailable 编排
- `components/`: health、AgentRun、ToolInvocation、SchedulerRun、RuntimeError 面板与状态视图
- `types/`: feature 内部展示类型
- `utils/`: 纯格式化、状态映射和错误展示 helper

不负责：

- AgentRun / ToolInvocation 详情页主体
- scheduler run 触发、重跑、取消、暂停或恢复
- 日志搜索、APM、实时监控墙
- 展示 raw prompt、完整模型推理链或未脱敏工具载荷

公开入口：

- `components/page/RuntimeDashboardPage.tsx`
- `hooks/useRuntimeDashboardPage.ts`

不要继续放入：

- 不要在 route 文件里新增 API 调用、query key、筛选状态或表格主体
- 不要在 `components/` 里直接访问 `apiClient`、拼 endpoint 或读取完整 API envelope
- 不要新增 runtime 写操作；V1 仅允许刷新与跳转
