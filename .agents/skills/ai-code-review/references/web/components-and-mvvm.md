# Web 组件与 MVVM 审查

本文件用于审查 React 组件职责、feature/shared 归属、props 边界和轻量 MVVM 拆分。

## 适用范围

触发信号：

- 修改 `src/app/components/**`、`src/features/**/components/**`、`src/shared/ui/**`。
- 新增表格、表单、timeline、risk panel、权限状态、空/错/加载态或可复用组件。
- 组件中出现 API response、query/mutation、权限判断、格式化、筛选和复杂 JSX 混合。

## 目标规范

- `features/<domain>` 承载业务组件、page/container、业务 hook、局部类型和领域格式化。
- `shared/ui` 只放跨域基础 UI，不含业务规则、业务 API、领域权限或完整 DTO。
- `app/components` 放应用级状态组件或 shell 级组件，不放业务域组件。
- 组件目录增长后必须分组：至少按 `components/`、`hooks/`、`view-models/`、`types/`、`utils/` 等职责组织，而不是长期平铺。
- 复杂页面采用轻量业务 Hook 编排：
  - query/mutation 提供服务端状态和动作。
  - 页面级业务 hook/container 组合状态、权限、派生字段和事件处理。
  - presentational component 只接收稳定 props 并负责渲染。
- props 应最小、稳定、语义化，不透传完整 API response 或万能 `raw` 对象。
- 非显然共享组件和复杂组件目录必须有 `README.md` 或 usage note；复杂边界、限制条件和设计取舍优先用中文注释说明。

## 审查步骤

1. 判断组件归属：app、feature、shared 中哪个职责最贴近。
2. 检查组件是否混合请求、权限、格式化、筛选、mutation 和 JSX。
3. 检查 props 是否暴露完整后端 DTO、ApiResponse、AuthState 或过宽 callback。
4. 检查状态覆盖：loading、empty、error、permission denied、sensitive masked 是否与功能风险匹配。
5. 检查公共组件是否有可理解的 API；非显然 shared UI 应有 usage note、README 或测试样例。
6. 检查目录是否已按职责分组，还是把组件、hooks、types 和 helper 无序堆在一起。

## Must-fix

- 新 shared UI 组件引入具体业务 API、权限策略、feature query 或完整业务 DTO。
- 复杂业务页面把请求、权限、表单、表格、mutation、错误处理和 JSX 全部堆进单个组件。
- 组件手写 API envelope 或直接依赖 `ApiResponse<T>`。
- 敏感字段、prompt、私有策略、完整模型推理链或工具参数被组件直接展示。
- 权限不足状态被当成 empty state，导致用户无法排查 request id。
- 一个组件目录平铺大量文件且无 `README` / usage note，导致组件边界、入口和复用方式不可判读。
- 复杂组件依赖关键边界但没有中文注释解释，reviewer 只能猜其安全或状态语义。

## Should-fix

- feature component props 偏宽，但仍只在单一业务域内使用。
- 页面级业务 hook 和 presentational component 未完全拆开，但当前 PR 可低成本拆出。
- 公共组件 API 非显然，缺少最小示例或测试覆盖。

## 常见误判

- 不是所有小组件都需要 MVVM 拆分；静态展示组件可以保持简单。
- feature-only 组件可以带领域语言，不需要强行抽到 shared。
- 不是所有组件都需要 README；只有 shared UI、复杂公共组件或非显然 API 需要补说明。
- 修改旧组件的文案或样式不必强制重构整个组件。

## Good example

```tsx
type PluginStatusBadgeProps = {
  health: "healthy" | "degraded" | "failed";
  status: "enabled" | "disabled";
};

export function PluginStatusBadge({ health, status }: PluginStatusBadgeProps) {
  return <StatusBadge tone={toPluginTone(health, status)} />;
}
```

组件只接收展示所需字段，不依赖完整 API response。

## Bad example

```tsx
export function SharedPluginPanel({
  response,
  auth,
}: {
  response: ApiResponse<PluginDetailResponse>;
  auth: AuthState;
}) {
  if (response.code !== 0) return <ErrorBox message={response.msg} />;
  if (!auth.capabilities.has("plugin.configure")) return null;
  return <PluginConfigForm plugin={response.data} />;
}
```

问题：shared 组件混入 envelope、业务 DTO、权限和领域表单。

## 验证建议

- 纯展示和 hook：`bun run --cwd apps/web test:unit`
- 复杂交互组件：`bun run --cwd apps/web test:ct`
- 影响 route/page 组合：`bun run --cwd apps/web build`
