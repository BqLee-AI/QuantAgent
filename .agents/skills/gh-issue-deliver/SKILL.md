---
name: gh-issue-deliver
description: 用于接手并交付本仓库 GitHub 开发 issue；当用户给出 issue 编号、要求实现 issue、处理 issue 关联 change 或从 issue 推进 PR 时使用，先读取 issue/评论，按 rooted OpenSpec 补齐或复用 change，再实现、验证、更新任务并收口。
license: Proprietary
compatibility:
  agent: "*"
  planning_mode_required: true
  structured_questioning_required: true
metadata:
  language: zh-CN
  scope: github-issue-delivery
  repo: BqLee-AI/QuantAgent
---

# gh-issue-deliver

这个 skill 用来解决 GitHub 开发 issue。它是 spec-aware 交付流程，不是“读到 issue 就直接改代码”。

核心目标是让 issue -> OpenSpec change -> implementation -> PR 形成同一条证据链。不要把实现判断只留在聊天里。

## 硬门槛：必须处于 Plan 模式

- 使用这个 skill 时必须处于 Plan 模式，并能使用结构化提问能力。
- 如果当前不在 Plan 模式，直接停下，要求用户切到 Plan 模式后再继续；不要读取大量上下文后继续推进。
- 不允许用普通聊天假装完成提问环节。
- 进入实现前必须至少发起一轮结构化提问，一次问 1-3 个会影响范围、验收或实现路径的问题。
- 如果 issue 和 OpenSpec 已经很清晰，问题也要用于确认“本轮是否按现有 artifacts 实施、哪些内容不进本轮、实现前是否需要再审核”。
- 如果当前代理环境没有 Plan 模式或结构化提问能力，不要跳过流程硬做；说明当前环境不满足本 skill 的交付门槛。

## 先读什么

开始前只读当前 issue 必需上下文：

1. `AGENTS.md`、`README.md`
2. issue 本体和评论：`gh issue view <id> --repo BqLee-AI/QuantAgent --json title,body,labels,comments,url,state`
3. issue 正文里链接的 OpenSpec change、设计文档、PRD、PR 或相关 issue
4. 影响设计或产品边界时，读相关 `docs/design/*.md`，必要时再读 `docs/prd/*.md`
5. 已有关联 change 时，读 `proposal.md`、`tasks.md`、`design.md` 和 `specs/**/spec.md`
6. 需要判断工程质量门槛时读 `.agents/skills/references/engineering-quality-gate.md`
7. 涉及 `apps/web/**`、前端 feature、route、API 调用、组件或运行时容器时，读 `.agents/skills/references/web-architecture-gate.md`
8. Web 工作涉及新增 feature、复杂 route、目录增长、shared 能力或文件拆分时，读 `.agents/skills/references/web-file-responsibility-and-feature-structure.md`
9. 需要执行清单时再读 `references/workflow.md`

不要批量扫仓库。不要创建、读取或更新 `docs/openspec`。

## 入口判断

先把 issue 收成四句话：

- 当前要解决的单一问题
- 为什么现在做
- 明确非目标
- 成功和失败信号

如果 issue 本身还很散，先问 1-3 个会改变实现路径的问题。不要问低价值偏好题，也不要把未确认设计问题直接下放给实现。

## 工程质量 Gate

进入实现前必须按 `.agents/skills/references/engineering-quality-gate.md` 完成硬检查：

- 是否已经读取根 `AGENTS.md`、最近层级 `AGENTS.md`、issue/comment、相关 design/PRD/OpenSpec 和目标模块现有实现。
- 是否说清目录/文件规划、职责边界、核心模型、接口字段、复用点、数据流、失败路径和验证入口。
- 前端工作是否覆盖 HeroUI、Tailwind、route/features/shared 分层、TanStack Query、组件拆分和页面状态。
- Web 工作是否对照 `.agents/skills/references/web-architecture-gate.md` 说清 route、app runtime、API/BaseApi/FeatureApi、query/mutation、业务 hook、view component、README、中文注释和目录分组边界。
- 复杂 Web 工作是否对照 `.agents/skills/references/web-file-responsibility-and-feature-structure.md` 说清具体文件职责，而不是把拆分决策留到编码时临场发挥。
- 后端工作是否覆盖薄 router、service/provider/repository/port、DTO/ORM/领域对象分层、审计权限和最小测试。
- OpenSpec artifacts 或 issue 是否足以指导实现；如果缺少目录蓝图、架构分层、模型/字段草案、复用判断、失败路径或验证口径，必须先补 artifacts 或追问，不能直接编码。

## 沉淀提醒

实现前和收口时都要判断是否需要提醒用户沉淀：

- 同类提醒第二次出现，或会长期影响 AI 行为：建议写入合适层级的 `AGENTS.md`。
- 设计文档和实现取舍发生变化：建议更新 `docs/design/` 或开后续 issue。
- 产品验收、待确认业务问题变化：建议更新 `docs/prd/`。
- 行为、架构、契约变化：必须关联或创建 OpenSpec change。
- 只是一次性 workaround 或环境问题：记录在 PR 说明，不沉淀成长期规则。

## OpenSpec 门槛

遵守本仓库规则：

- 影响行为、架构或跨文件契约的工作，必须落到 `openspec/changes/<change-id>/`。
- 一个 PR 只服务一个 change，不混入无关 artifacts。
- 实现前必须读取该 change 的 `proposal.md`、`tasks.md` 和受影响 spec。
- 更新 change 后必须运行：

```bash
openspec validate <change-id> --type change --strict --json
```

处理方式：

1. issue 已明确关联 active change：复用它，先读 artifacts，再实现。
2. issue 只关联 archived/stable spec：判断是否需要新 change；需要时先补 active change。
3. issue 没有 OpenSpec，但影响行为、架构或跨文件契约：先创建或更新 change，走 OpenSpec-only PR 审核后再实现。
4. issue 仅文档、仓库维护或很小的局部修复：可以记录“不需要 OpenSpec”的理由，再按普通小改处理。

当需要新建或重写 OpenSpec artifacts 时，优先使用 `.agents/skills/openspec-propose` 的流程；当已有 change 可实施时，优先使用 `.agents/skills/openspec-apply-change` 的流程。

## OpenSpec PR 审核门槛

OpenSpec 文档本身可能不合适，不能只在本地生成后继续写代码。只要新建或大幅更新了 OpenSpec artifacts，必须：

1. 运行 `openspec validate <change-id> --type change --strict --json`。
2. 使用 `.agents/skills/gh-pr-create` 创建一个 OpenSpec-only PR。
3. PR 范围只包含本 change 的 `proposal.md`、`design.md`、`tasks.md`、`specs/**/spec.md` 和必要说明。
4. 等待维护者在 PR 下明确评论“没问题”或批准。
5. 获得明确认可后，基于该 OpenSpec PR 分支或当前工作分支创建实现分支并进入代码实现；不需要等待 OpenSpec PR 合入。

在 OpenSpec-only PR 获得维护者明确认可前，不允许：

- 实现代码。
- 添加依赖。
- 改 API / Web / DB / plugin / Agent 运行时代码。
- 把 spec artifacts 和 implementation 混在同一个 PR 里。

如果 issue 已经关联一个维护者明确认可过的 OpenSpec PR 或已合入的 OpenSpec change，可以进入实现；如果只是本地 artifacts 或未获明确认可的 PR，必须先完成审核门槛。

不要把 design review、tasks planning 或验证入口设计写成 OpenSpec 外的第二套流程。它们是在继续加固同一个 change：

- `proposal.md`：为什么现在开这个 change。
- `design.md`：主资产、路径、边界、失败链路和取舍。
- `specs/**/spec.md`：能力级 requirement 和 scenario。
- `tasks.md`：依赖图、并行切片、审核点和验证动作。

## 任务组织

`tasks.md` 或执行计划要体现依赖关系，而不是线性施工口号：

- 阻塞项：不先完成会让后续边界漂移。
- 可并行项：写入边界不重叠，且不依赖彼此结果。
- 集成点：需要统一审查契约、文档或验证结果。
- 每个任务写清输入、输出和写入边界。

只有当前环境和用户明确允许委派时，才把独立任务交给子 Agent；否则在本线程完成，并说明没有委派的原因。

开始实现前检查 `tasks.md` 是否足够执行：

- 是否有串行阻塞项，而不是“后端/前端/测试”三段式？
- 是否标出可并行任务和写入边界？
- 是否有 review gate，例如契约、设计、schema、迁移或风险路径检查？
- 是否把验证动作放到合适节点，而不是全部堆到最后？
- 是否把 issue 评论中的约束合并进任务输入？

如果 tasks 太弱，先补强 artifacts 或向用户说明需要暂停审核。

## QuantAgent 实现边界

实现时保持这些边界：

- `apps/api/` 只承载 HTTP 边界，不把核心领域逻辑塞进 router。
- `apps/web/` 负责 React + Vite 前端；保持测试层级清楚。
- `packages/core/` 承载共享配置、数据库、Alembic、错误和基础能力。
- `packages/contracts/` 承载跨前后端契约与生成物边界。
- Agent、plugin SDK、adapters 分别遵守对应 package 边界。
- 真实执行、真实凭证、生产账户和 live trading 不作为默认实现对象。
- 插件配置走 schema-driven form；不要引入插件自定义前端组件。
- 不提交 `runtime/` 本地产物、secrets 或真实 `.env`。

新增 package、依赖或技术栈时要额外谨慎：

- 先确认现有 workspace 和 package 边界是否已经足够。
- 新 package 必须有明确复用方、依赖方向和契约真源；不要为“以后可能”提前创建。
- 较新的库/API 不能只靠模型记忆判断；以 lockfile、已安装版本、官方文档和本地验证为准。
- AI review 提到的 API 兼容性问题要逐条核实，可能是基于旧版本的错误建议。

## 验证

选择当前风险需要的最小 harness：

- OpenSpec：`openspec validate <change-id> --type change --strict --json`
- API：`cd apps/api && uv run python -m unittest discover -s src/tests`
- Web unit：`bun run --cwd apps/web test:unit`
- Web E2E：`bun run --cwd apps/web test:e2e`
- Web CT：`bun run --cwd apps/web test:ct`
- 前端静态检查：`bun run lint`、`bun run build`、`bun run fmt:check`

不要为了“完整”引入外部网络、真实交易服务、真实凭证或重型 E2E。

## 收口

完成后返回：

- issue URL 和关联 OpenSpec change
- 改动摘要
- 已完成的任务和仍未决的点
- 运行过的验证命令与结果
- 是否需要后续沉淀到 AGENTS、docs/design、docs/prd 或新 issue
- 如果没有 OpenSpec、没有委派或跳过某类验证，写清原因
