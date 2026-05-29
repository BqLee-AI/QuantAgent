## models feature

负责 `/models` 管理台页面的模型供应商配置、模型列表管理、固定任务模型预设与调用记录展示。

入口：
- route: `src/routes/_app/(workspace)/models/index.tsx`
- page: `components/page/ModelsPage.tsx`
- page hook: `hooks/useModelsPage.ts`

当前职责：
- `api/`: 模型相关 REST contracts 与 endpoint 封装
- `queries/`: query keys 与 `useQuery` 读取逻辑
- `mutations/`: `useMutation` 与 invalidate 逻辑
- `hooks/`: 页面级业务编排、表单业务状态
- `components/page/`: 页面装配
- `components/provider-list/`: 供应商列表与筛选
- `components/provider-form/`: 供应商表单展示
- `components/provider-models/`: 模型列表与弹窗
- `components/provider-status/`: 调用记录与状态统计
- `components/preset-board/`: 固定任务预设板
- `components/shared/`: 仅限本 feature 复用的纯展示组件
- `types/`: feature 内部 UI 类型
- `utils/`: 纯格式化和无副作用 helper

不负责：
- ProviderPolicy 编辑器
- budget / cost governance
- 非 `/models` 路由的通用 UI

公开入口：
- `components/page/ModelsPage.tsx`
- `hooks/useModelsPage.ts`

不要继续放入：
- 不要在 route 文件里新增 query、mutation、弹窗状态或业务表单逻辑
- 不要在 `components/` 里直接调 API、拼 query key 或处理 invalidate
- 不要把 feature DTO、query、页面状态重新平铺回根目录
