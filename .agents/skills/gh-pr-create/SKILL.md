---
name: gh-pr-create
description: 用于为本仓库准备、撰写和创建 GitHub PR；当实现已完成，或 OpenSpec artifacts 需要先单独提 PR 审核时使用，负责从 issue/OpenSpec change 形成 PR 说明、提交证据链、选择验证结果并推送分支。
license: Proprietary
compatibility:
  agent: "*"
metadata:
  language: zh-CN
  scope: github-pr-create
  repo: BqLee-AI/QuantAgent
---

# gh-pr-create

这个 skill 用来把已经完成的本地改动整理成可 review 的 PR，也用于把新建或大幅更新的 OpenSpec artifacts 单独提交审核。它不负责把未收敛需求直接变成实现。

## 先读什么

1. 根 `AGENTS.md` 和改动路径下更近的 `AGENTS.md`
2. `git status --short --untracked-files=all`
3. `git diff --stat` 和关键 diff
4. 关联 issue：`gh issue view <id> --repo BqLee-AI/QuantAgent --json title,body,labels,comments,url,state`
5. 关联 OpenSpec change 的 `proposal.md`、`tasks.md`、`design.md`、`specs/**/spec.md`
6. 需要判断工程质量门槛时读 `.agents/skills/references/engineering-quality-gate.md`
7. 涉及 `apps/web/**`、前端 feature、route、API 调用、组件或运行时容器时，读 `.agents/skills/references/web-architecture-gate.md`
8. 需要对照 PR 说明结构时再读 `references/pr-body.md`

不要把未提交、无关或用户已有脏改动混进 PR。当前工作区有无关变更时，先说明并只 stage 自己负责的文件。

## PR 前检查

创建 PR 前必须确认：

- 分支不是过期的本地 `main`，已经基于远端主线或清楚说明差异。
- PR 只围绕一个 issue 或一个 OpenSpec change。
- OpenSpec-only PR 只能包含 proposal、design、specs、tasks 和必要说明，不能混入实现代码。
- Implementation PR 必须基于维护者已明确认可或已合入的 OpenSpec artifacts；如果 artifacts 还没过 PR review，先创建 OpenSpec-only PR。
- OpenSpec tasks 已按真实完成状态更新。
- 影响行为、架构或契约的改动已跑 `openspec validate <change-id> --type change --strict --json`。
- 验证命令和结果可被写进 PR，不用“应该没问题”代替。
- 新 package、依赖、生成物或 runtime 边界变化有明确真源和说明。
- 工程质量 gate 已体现在 diff 或 PR 说明中：目录/文件规划、职责边界、核心模型、接口字段、复用点、数据流、失败路径、验证入口和必要注释都有交代。
- Web PR 已体现在 diff 或 PR 说明中：route、app runtime、API/BaseApi/FeatureApi、query/mutation、业务 hook、view component、README、中文注释和目录分组是否符合 `web-architecture-gate.md`。
- 若跳过组件拆分、service/repository/port、注释或测试，必须有基于范围和风险的理由。
- 没有提交 secrets、真实 `.env`、runtime 私有内容、缓存或构建产物。

## PR 说明要求

PR body 要写清证据链，而不是只列改了什么：

- 关联 issue / OpenSpec change。
- 为什么这样改，依据来自 issue、评论、OpenSpec、设计文档还是验证结果。
- 为什么这样拆分，为什么新增或不新增抽象，为什么复用或不复用既有能力。
- 实现是否遵循 design.md 中的目录/文件规划、模型/DTO/schema/API 字段草案；偏离时说明原因。
- 改动摘要，按边界组织，不按文件流水账。
- 验证命令和结果。
- 未验证项、残余风险、非目标和原因。
- 跳过组件拆分、注释、service/repository/port 或某类测试时，说明判断依据。
- 对 AI review 可能关注的点提前说明：较新技术栈、版本差异、非目标、为什么没有采用某个常见建议。

默认中文。技术命令、路径、label、change id 保持原文。

## gh 命令流程

优先使用非交互式命令：

```bash
git status --short --untracked-files=all
git diff --stat
git add <only-owned-files>
git commit -m "<type>(scope): <中文摘要>"
git push -u origin <branch>
gh pr create --repo BqLee-AI/QuantAgent --base main --head <branch> --title "<title>" --body-file <file>
```

提交信息使用中文 Angular 风格，例如：

- `feat(web): 增加事件路由页面骨架`
- `fix(api): 收敛错误响应契约`
- `docs(agents): 补充 issue 和 PR 控制面规则`

不要用交互式 `gh pr create` 让关键信息散在提示流里。

## 创建后

创建 PR 后回读：

```bash
gh pr view <number> --repo BqLee-AI/QuantAgent --json title,url,state,reviewDecision,headRefName,baseRefName
```

返回给用户：

- PR URL
- 关联 issue / change
- 提交摘要
- 验证结果
- 已知风险或等待 review 的点

如果没有创建 PR，只准备了 PR body 或提交，也要说明停在哪一步以及原因。
