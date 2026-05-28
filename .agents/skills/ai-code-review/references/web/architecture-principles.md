# Web 架构审查基准

本文件定义 `apps/web` AI Code Review 的目标架构基准。规划和实现阶段的共享规范真源是 `.agents/skills/references/web-architecture-gate.md`；本文件只补充 review 时如何把这些规范转成 finding。

现有实现可以帮助理解迁移背景，但不能作为新代码的规范模板。

## 审查原则

- 以目标架构审查新增和被修改代码：`.agents/skills/references/web-architecture-gate.md`、`apps/web/AGENTS.md`、`docs/design/09-frontend-architecture-design.md`、React / TanStack Query / TanStack Router 主流实践优先于当前偶然实现。
- 不要求一个 PR 清完全部历史债务；未触碰的旧问题列为 residual risk 或 defer。
- 如果本次变更在旧的不规范文件中继续新增请求、状态、权限、表单、业务格式化或复杂 JSX，应判定为扩大债务。
- Review finding 必须聚焦当前 diff 新增或修改的行为，不用全局重构建议压垮局部 PR。
- 文件职责单一是 `apps/web` 的基础 review 标准。拆文件不是为了形式，而是让 AI 和维护者能根据文件名定向阅读，避免把无关 API、DTO、状态机、provider、hook、policy、UI 和 fixture 一起塞进上下文。
- 中文注释、目录说明和 usage note 也是架构的一部分。对于非显然边界和复杂目录，不能默认靠命名猜。

## 目标分层

```text
src/
  app/       # bootstrap、providers、router、layout、应用级错误边界
  routes/    # TanStack Router 文件路由入口：loader/search/beforeLoad/redirect/page 组合
  features/  # 业务域：api、queries、mutations、view-model hooks、components、types
  shared/    # 跨域基础能力：api client、auth、config、errors、ui、utils
  styles/    # 全局 tokens、layout fallback、HeroUI/Tailwind 主题
  debug/     # 开发态诊断入口，生产不可见
```

目录职责：

- `app` 不放业务规则，不直接调用业务 API。
- `routes` 不承载复杂业务 UI 或服务端状态逻辑。
- `features/<domain>` 是业务 UI、query/mutation、领域组件和 view model 的默认落点。
- `shared` 只放跨业务域复用且不含具体业务流程的基础能力。
- `styles` 维护设计系统底座，不为单个页面承载业务样式堆叠。
- `debug` 只服务开发诊断，不进入正式导航或生产路由。

目录组织也应保持可定位：

- 同一 capability 目录下如果同时存在组件、hooks、types、api、utils、tests，应优先拆成子目录，而不是长期平铺。
- 当目录增长到需要读文件名列表才能猜职责时，就已经需要分组或补 README。
- 复杂目录必须有 `README.md` 或最小 usage note，说明职责、公开入口、子目录含义和禁止继续堆放的内容。

## 文件职责基准

- 一个文件应只有一个主要职责和一个主要修改理由。
- `client.ts`、`base-api.ts`、feature `api.ts`、`queries.ts`、view-model hook、presentational component、policy、types 和 test fixture 应尽量分离。
- 注释和文档也要按职责落位：文件内非显然设计写中文注释，目录级约束写 `README.md` 或 usage note。
- 不用固定行数判断是否需要拆分；如果同一文件同时修改请求协议、状态机、React 生命周期、权限策略和渲染，就已经违反职责单一。
- 当“少建文件”和“职责清晰”冲突时，优先职责清晰。
- 旧文件已经过厚不是新增代码继续堆叠的理由；触碰旧代码时至少要把本次新增逻辑收敛到目标边界。

## 债务处理口径

- `must-fix`：新增代码直接违反目标分层，或在旧债上继续叠加同类复杂度。
- `should-fix`：当前 PR 内可低成本收敛，例如把新增请求移出 route。
- `defer`：需要后续迁移 issue 才能处理的大范围历史结构。
- `residual risk`：审查中看到但当前 diff 未触碰的问题。

## 评审时先问的三个问题

1. 这段新增逻辑属于路由入口、业务功能、跨域基础能力，还是开发诊断？
2. 当前文件是否是该职责的目标落点，还是只是历史上刚好写在这里？
3. 如果以后同类页面复制这段代码，会扩大架构债务还是形成可复用模式？

## 常见 must-fix 信号

- 新 route 直接调用底层 API、维护服务端列表状态并渲染复杂表格。
- `shared/ui` 组件引入具体业务 API、权限策略或完整后端 DTO。
- `app` provider 或 layout 中加入业务域判断、插件状态流转或审批动作。
- 页面把 REST 快照长期复制到 React state / Zustand，并绕过 TanStack Query。
- debug 代码进入生产路由、正式导航或用户可见业务页面。
- 新增或重构文件把 API 调用、DTO/types、状态机、provider、hook、policy、UI 或 fixture 混成多个变化原因。
- 复杂目录长期平铺几十个文件，没有 `components/`、`hooks/`、`types/` 等职责分组，也没有 README 解释边界。
- 非显然安全/状态/权限边界没有中文注释，只能靠 reviewer 或 AI 猜测实现意图。
