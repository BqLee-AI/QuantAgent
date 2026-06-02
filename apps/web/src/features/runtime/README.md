# Runtime 审计

`features/runtime` 负责 `/runtime` 的 Runtime audit chat V1。首版页面用 Router Agent / AI intake 作为受控 fixture 样例，展示 `industry.analysis.requested -> EventIntakeDecisionV1 -> event.routed` 的审计流。

## 入口

- route: `src/routes/_app/(workspace)/runtime/index.tsx`
- page: `components/page/RuntimeAuditPage.tsx`
- page hook: `hooks/use-runtime-audit-page.ts`
- runtime API registry: `app/runtime/runtime.factory.ts`

## 子目录职责

- `api/`: Runtime audit read contract 和受控 fixture API；当前不声明生产 endpoint。
- `queries/`: TanStack Query key 和 query hook，通过 `useApis().runtimeAudit` 读取。
- `hooks/`: 页面筛选、选中消息、刷新和派生状态。
- `components/`: page、filter bar、conversation/message、detail、health strip 和状态视图。
- `types/`: UI 展示类型与安全详情类型。
- `utils/`: 格式化、脱敏、fixture 构造和筛选纯函数。

## 不负责

- 不做通用聊天机器人，不允许用户自由 prompt 驱动模型或 tool。
- 不实现生产审计 read model、后端持久化或 scheduler 控制。
- 不展示 raw prompt、完整 chain-of-thought、provider raw response、secret、未脱敏工具输入输出或完整原文。

## 安全边界

详情视图只能展示 `safe_details`。新增字段时必须先经过 `runtime-audit-sanitize.ts` 或后端等价脱敏结果，不能把 provider raw response、secret-bearing config、ORM object 或 plugin instance 直接传给组件。
