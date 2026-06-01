## mainflow feature

负责 QuantAgent V1 操盘主链路占位页面：

- `/`
- `/events`
- `/events/:eventId`
- `/events/:eventId/audit`
- `/approvals`
- `/approvals/:approvalId`
- `/approval-link/:token`
- `/runtime`
- `/runtime/agents/:runId`
- `/runtime/tools/:invocationId`
- `/plugins`
- `/plugins/:pluginId`
- `/settings`

入口：

- route: `src/routes/_app/(workspace)/**` 与 `src/routes/(public)/approval-link/$token.tsx`
- page exports: `MainflowSections.tsx`

当前职责：

- `pages/`: 页面级占位内容和页面装配
- `components/`: 主链路复用展示组件
- `mock-data.ts`: 仅供正式占位页面使用的静态结构化样例
- `utils/`: 纯展示格式化 helper

不负责：

- `/models` 的真实治理实现
- debug 工作台页面状态预览
- 共享 API、query、mutation 和运行时 client

不要继续放入：

- 不要在 route 文件里直接堆页面主体 JSX
- 不要把插件治理、模型治理以外的新正式页面继续平铺到别的临时目录
- 不要把调试态页面或 query 参数实验混入这里
