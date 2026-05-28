# Web Routes 与 Layout 审查

本文件用于审查 TanStack Router route、layout shell、debug route 和路由生成物相关变更。

## 适用范围

触发信号：

- 修改 `src/routes/**`、`src/app/router.tsx`、`src/app/layouts/**`、`src/routeTree.gen.ts`。
- 新增 route、loader、search params、beforeLoad、redirect、workspace shell、public page 或 debug route。

## 目标规范

- route 文件只负责 `createFileRoute`、loader/search/beforeLoad、redirect、权限入口和页面组合。
- route 可以把 search、params 或 loader 结果传给 feature page，但不能实现业务编排 hook。
- 复杂页面内容进入 feature page、业务 hook 和 components。
- 公开页面保持在 app shell 外；受保护后台页统一挂到 workspace shell 下。
- 权限失败通过 auth/capability 边界处理，不能在页面组件里绕过。
- `src/routeTree.gen.ts` 是生成文件，不手写业务逻辑。
- debug route 必须开发态隔离，生产不可见，不进入正式导航。

## 审查步骤

1. 判断 route 变更是入口组合、权限/search 逻辑，还是业务 UI/请求被塞进 route。
2. 检查 route 是否引入 `apiClient`、业务 DTO、表格状态、复杂表单、权限动作或业务格式化。
3. 检查 route 是否定义 `useXxxPage()` 这类业务 hook；如果定义了，应移动到 feature `hooks/`。
4. 检查 public / protected route 是否落在正确 shell。
5. 检查 debug route 是否通过 runtime/development split 隔离生产。
6. 检查 `routeTree.gen.ts` 是否只来自生成流程。

如果 route 承载了业务请求、表格、表单、弹窗或业务 hook 实现，继续读取 `.agents/skills/references/web-file-responsibility-and-feature-structure.md`，给出应拆入的 feature 目录结构。

## Must-fix

- 新增 route 直接请求业务 API、维护服务端列表状态或处理复杂 mutation。
- 在 route 文件中继续追加表格、弹窗、筛选、权限动作和业务格式化，扩大历史厚 route 债务。
- 在 route 文件中实现页面级业务 hook、表单 hook 或列表筛选 hook。
- 受保护页面绕过 workspace auth/capability 边界。
- 手写或修改 `routeTree.gen.ts` 的业务逻辑。
- debug route 在生产构建或正式导航中可见。

## Should-fix

- route 内组件略厚，但只是当前 PR 新增的小型静态占位；建议尽早抽到 feature page。
- search params 解析分散，可低成本收敛到 route schema / helper。
- layout 中出现可复用 UI 片段，可移入 app component 或 shared UI。

## 常见误判

- route 可以做 redirect、beforeLoad 和 search params，这是路由职责。
- 轻量 placeholder 页面在骨架期可以存在，但不能在正式功能中继续承载业务请求。
- 修改旧 route 的文案或样式不必强制重构整个 route。

## Good example

```tsx
export const Route = createFileRoute("/_app/plugins/")({
  validateSearch: pluginSearchSchema,
  component: PluginsRoute,
});

function PluginsRoute() {
  const search = Route.useSearch();
  return <PluginsPage search={search} />;
}
```

## Bad example

```tsx
export const Route = createFileRoute("/_app/plugins/")({
  component: function PluginsRoute() {
    const [rows, setRows] = useState<PluginRow[]>([]);
    const [modalOpen, setModalOpen] = useState(false);

    useEffect(() => {
      void apiClient.get("/plugins").then(setRows);
    }, []);

    return <LargeTable rows={rows} modalOpen={modalOpen} />;
  },
});
```

问题：route 同时承担请求、服务端状态、弹窗状态和复杂页面 UI。

## 验证建议

- 路由结构、layout 或生成物：`bun run --cwd apps/web build`
- 路由交互：按风险选择 `bun run --cwd apps/web test:unit`、`test:ct` 或 `test:e2e`
- debug route：人工确认生产入口使用 noop API，开发入口才 attach debug routes。
