---
name: gh-issue-create
description: 用于为本仓库创建、拆分、补写或批量整理 GitHub 开发 issue；当讨论、设计差距、OpenSpec seed、PR 评论或用户粗略需求需要先被压成可协作 issue 时使用，输出 why now、范围、非目标、未决点、验收、验证和 OpenSpec 处理。
license: Proprietary
compatibility:
  agent: "*"
metadata:
  language: zh-CN
  scope: github-issues
  repo: BqLee-AI/QuantAgent
---

# gh-issue-create

这个 skill 只负责把工作收敛成 QuantAgent 仓库可接手的 GitHub issue。它不是用户反馈模板，也不负责直接实现。

目标是把同一个问题从 discussion / 口头需求 / 设计差距，压成后续 OpenSpec 和 PR 能继续接住的协作对象。不要为了“信息完整”堆材料；要把判断写到正确位置。

## 先读什么

只读当前 issue 需要的上下文，避免批量扫仓库：

1. `AGENTS.md`、`README.md`
2. 相关 `docs/design/*.md`；设计文档是长期真相层
3. 相关 `docs/prd/*.md`；PRD 是产品表述和待确认项
4. 用户点名的 `openspec/changes/<change-id>/proposal.md`、`design.md`、`tasks.md`、`specs/**/spec.md`
5. 已有相关 GitHub issue 或 PR：`gh issue view <id> --repo BqLee-AI/QuantAgent --json title,body,labels,url,state`
6. 用户提到的 PR 评论、review finding 或失败日志
7. 需要判断工程质量门槛时读 `.agents/skills/references/engineering-quality-gate.md`
8. 涉及 `apps/web/**`、前端 feature、route、API 调用、组件或运行时容器时，读 `.agents/skills/references/web-architecture-gate.md`
9. 需要对照原则时再读 `references/issue-guidelines.md`
10. 需要同步或选择标签时再读 `references/label-policy.md`

不要创建或引用 `docs/openspec`。本仓库只使用根目录 `openspec/`。

## 核心判断

一个开发 issue 必须收住一个可验证的不确定性，而不是功能篮子或施工流水账。创建前先确认：

- 单一问题：这一刀到底解决哪个缺口？
- 为什么现在做：它正在阻塞哪个设计、实现、验证或后续 issue？
- 范围边界：哪些内容明确不进本轮？
- 验收口径：什么算成立，什么明确不成立，什么是失败信号？
- OpenSpec 关系：是否需要新建或关联 `openspec/changes/<change-id>/`？
- 架构/分层风险：是否涉及组件拆分、service/repository/port、契约、持久化、审计或权限边界？

如果这些问题还答不清，不要硬造 `status:ready` issue。先问用户一个聚焦问题，或创建 `status:needs-review` / `status:blocked`。

涉及 Web 的 issue 不能只写“做页面”或“接 API”。必须根据 `.agents/skills/references/web-architecture-gate.md` 收住 route、runtime/API、query/mutation、业务 hook、view component、README、中文注释和目录分组边界，并写进 `子任务树` 或 `架构 / 分层风险`。

## 控制面沉淀判断

创建 issue 时要判断这件事是否还需要沉淀到其他载体，并在 issue 的 `OpenSpec 处理` 或 `待确认问题` 中说清楚：

- 长期协作规则、反复出错的操作边界：沉淀到合适层级的 `AGENTS.md`。
- 行为、架构、跨模块契约、风险边界变化：开或关联 `openspec/changes/<change-id>/`。
- 稳定模块边界、架构取舍、运行时原则：更新 `docs/design/`。
- 产品表述、验收样例、待确认业务问题：更新 `docs/prd/`。
- 一次性执行细节、临时调试命令、尚未确认的想法：只留在 issue / PR，不写进长期规则。

issue 不需要替这些资产全部改完，但必须提醒后续落点。不要把同一判断只留在聊天里。

## QuantAgent 项目边界

写 issue 时要贴合这些仓库事实：

- 产品是事件驱动量化智能系统，不是通用聊天机器人。
- 主流程围绕 Source Plugin、Event Bus、Router Agent、Industry Package、AgentRuntime、Decision / Policy Gate、Notification、Approval、Executor、Persistence、WebSocket。
- 真实执行必须经过 Decision / Policy Gate；默认不要把 live trading、真实券商、真实密钥或生产执行写进当前 issue。
- API 边界在 `apps/api/`，核心领域逻辑不放在 FastAPI router。
- Web 边界在 `apps/web/`，前端使用 React + Vite；插件配置采用 schema-driven form，不接收插件自定义前端组件。
- 共享基础能力在 `packages/core/`；跨端契约和生成物边界在 `packages/contracts/`。
- Agent/workflow、plugin SDK、adapters 当前分别预留在 `packages/agent/`、`packages/plugin-sdk/`、`packages/adapters/`。
- `runtime/`、真实 `.env`、secrets、私有策略、交易密钥和本地数据不得进入 issue 的交付物。

## Issue 正文结构

除非用户给了明确模板，否则正文使用以下结构，保持中文、具体、可审核：

```markdown
## 背景 / 为什么现在做

## 当前要收住的问题

## 目标

## 明确不做

## 相关上下文

## 前置依赖

## 待确认问题

## 子任务树

## 验收口径

## Harness / 验证要求

## 架构 / 分层风险

## OpenSpec 处理
```

写法要求：

- `背景 / 为什么现在做` 写阻塞链路和漂移风险，不写泛泛价值。
- `当前要收住的问题` 用一句话定义唯一问题。
- `目标` 写 3-5 条边界，不要写成愿景。
- `明确不做` 要点名容易被误带入的未来能力。
- `相关上下文` 链接 issue、PR、OpenSpec、设计文档段落或日志。
- `前置依赖` 写清是否 blocked；没有依赖也明确写“无已知阻塞”。
- `待确认问题` 只放实现者不能自行拍板的问题。
- `子任务树` 面向收敛，不要堆无依赖的待办项；可标注串行/可并行/审核点。
- `验收口径` 至少覆盖“必须成立 / 明确不成立 / 失败信号”。
- `Harness / 验证要求` 只写当前风险需要的最轻验证。
- `架构 / 分层风险` 写清需要由 OpenSpec 或实现前设计收住的职责边界、复用点、数据流、失败路径和验证入口；不涉及时也明确说明“无已知跨边界风险”。
- `OpenSpec 处理` 明确是“需新建 change”“关联现有 change”“仅文档/仓库维护，暂不需要 change”中的哪一种。

## 质量门槛

写完 issue 草稿后自查：

- 是否能从标题看出问题边界，而不是只有“优化”“完善”“支持”？
- why now 是否解释了不做会导致什么后续漂移？
- 非目标是否足够阻止 AI 把未来 phase 偷带进来？
- 验收是否可被测试、review 或人工检查证明？
- Harness 是否匹配当前风险，没有过重也没有缺失关键验证？
- 架构 / 分层风险是否具体，是否覆盖前端组件拆分、后端 service/repository/port、DTO/ORM 分层、审计权限或契约影响？
- Web issue 是否已对照 `web-architecture-gate.md` 写清 runtime/API/query/hook/component/README 边界，而不是把分层决策留给实现者？
- OpenSpec 关系是否明确，没有把行为变更伪装成普通 TODO？
- 若涉及新 package 或目录，是否说明为什么现有 `apps/` / `packages/` 边界接不住？

## OpenSpec 规则

- 影响行为、架构或跨文件契约的 issue，应要求先有 `openspec/changes/<change-id>/`。
- 已有 change 时，issue 要链接 proposal/tasks/spec；不要另造并行说明。
- 没有 change 时，issue 可以要求后续先用 `openspec-propose` 生成 artifacts，再实现。
- 不要把稳定 spec 手动挪到 `openspec/specs/`；完成后走 archive workflow。

issue 和 proposal 可以讲同一个问题，但职责不同：

- issue 面向协作队列，回答“为什么这个问题现在值得排进来”。
- proposal 面向 OpenSpec change，回答“为什么要为它开一组正式 spec artifacts”。
- 不要把 issue 写成 proposal 的复制品，也不要让 proposal 从零猜 issue 已经收住的边界。

## 标签和 gh

- 默认 repo：`BqLee-AI/QuantAgent`。
- 创建 issue 前按 `references/label-policy.md` 选择标签。
- 如果远端缺少本 skill 的标准标签，先运行：

```bash
python3 .agents/skills/gh-issue-create/scripts/sync_repo_labels.py --repo BqLee-AI/QuantAgent
```

- 使用非交互式 `gh issue create`，正文先写入临时 markdown 文件，再用 `--body-file`。
- 创建后必须回读：

```bash
gh issue view <number> --repo BqLee-AI/QuantAgent --json title,labels,url,state
```

如果标签不完整，立即用 `gh issue edit` 修正；不要只挂 GitHub 默认 `enhancement` / `documentation`。

## 返回给用户

创建或整理完成后至少返回：

- issue 标题和 URL
- label 集合
- 它现在是 `needs-review`、`ready` 还是 `blocked`
- 关联的 OpenSpec change 或下一步应创建的 change
