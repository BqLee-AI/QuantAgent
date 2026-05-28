---
name: gh-pr-comments
description: 用于处理本仓库 PR review comments、Copilot/AI 审查建议、CI 评论和维护者反馈；当用户要求修 PR 评论、评估 review、回复评论或继续修改 PR 时使用。
license: Proprietary
compatibility:
  agent: "*"
metadata:
  language: zh-CN
  scope: github-pr-comments
  repo: BqLee-AI/QuantAgent
---

# gh-pr-comments

这个 skill 用来处理 PR 评论。评论可能来自维护者、CI、Copilot 或其他 AI reviewer；它们都是输入，不是自动正确的结论。

## 先读什么

1. 根 `AGENTS.md` 和改动路径下更近的 `AGENTS.md`
2. PR 元信息：

```bash
gh pr view <pr> --repo BqLee-AI/QuantAgent --json title,body,state,reviewDecision,headRefName,baseRefName,comments,reviews,files,url
```

3. 行级 review thread：

```bash
gh api repos/BqLee-AI/QuantAgent/pulls/<pr>/comments
```

4. 关联 issue、OpenSpec change、设计文档和 CI 日志
5. 需要判断工程质量门槛时读 `.agents/skills/references/engineering-quality-gate.md`
6. 涉及 `apps/web/**`、前端 feature、route、API 调用、组件或运行时容器时，读 `.agents/skills/references/web-architecture-gate.md`
7. 需要分类处理时再读 `references/comment-triage.md`

## 分类原则

逐条把评论分成：

- `must-fix`：真实 bug、契约破坏、安全问题、测试缺口、违反仓库规则。
- `should-fix`：合理改进，范围内且成本低。
- `needs-discussion`：会改变范围、设计、package 边界或 OpenSpec。
- `defer`：有价值但应进后续 issue。
- `not-applicable`：基于旧代码、旧版本 API、误读项目边界或与当前非目标冲突。

不要因为评论来自 AI 就全接，也不要因为来自 AI 就直接忽略。用代码、版本、文档、测试和项目规则判断。

如果评论指出组件拆分、HeroUI/Tailwind、薄 router、service/repository/port、DTO/ORM 分层、注释、OpenSpec 质量或验证缺口，必须对照 `.agents/skills/references/engineering-quality-gate.md` 判断是否属于 must-fix 或 should-fix；Web 评论还必须对照 `.agents/skills/references/web-architecture-gate.md` 判断 runtime/API/query/hook/component/README 边界。不能用“当前能跑”作为跳过理由。

## 判断较新技术栈

如果评论涉及库 API、框架行为或最佳实践：

- 先看本仓库 lockfile、package version、pyproject 和现有代码。
- 再看官方文档或当前版本 release notes；不要只靠模型记忆。
- 判断建议是否适用于当前版本。AI 可能引用旧版 React、TanStack Router、HeroUI、FastAPI、Pydantic、SQLAlchemy、DeepAgents 或 OpenSpec 习惯。
- 能用小测试验证的，用最小验证替代争论。

## 修改规则

- 只修评论要求且属于当前 PR 范围的内容。
- 如果评论暴露 OpenSpec、设计文档、工程质量 gate 或任务不一致，先更新对应 artifact，再改代码。
- 如果评论要求扩大范围，回复说明需要后续 issue 或新 change。
- 如果评论错误，回复简短证据：当前代码、版本、文档或验证结果。
- 修改后补跑受影响的最小验证，并更新 PR 评论或 PR body。

## 回复格式

回复要短、可核查：

- 已修：说明改了什么和验证命令。
- 不适用：说明依据，不写情绪化反驳。
- 延后：说明后续 issue/change 应承接什么。
- 需要讨论：列出需要维护者拍板的问题。

## 收口

返回给用户：

- 评论分类结果
- 已修改文件和原因
- 已回复或建议回复的评论
- 运行的验证
- 仍需人工决策的评论
