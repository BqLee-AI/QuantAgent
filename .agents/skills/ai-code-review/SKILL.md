---
name: ai-code-review
description: 用于对本仓库 PR、commit、diff 或代码变更做 AI Code Review；当用户要求 review PR、review commit、review diff、代码审查、CR 规范检查、AI CR 或检查变更是否符合 QuantAgent 模块边界时使用。
license: Proprietary
compatibility:
  agent: "*"
metadata:
  language: zh-CN
  scope: ai-code-review
  repo: BqLee-AI/QuantAgent
---

# ai-code-review

这个 skill 用来主动审查 QuantAgent 的代码变更。它不是通用语言 checklist，也不是替代维护者判断的自动结论。

目标是让 review 基于本仓库真源、当前 diff 和模块 reference，找出真实 bug、架构边界破坏、安全风险、契约漂移、测试缺口和需要维护者讨论的设计问题。

## 先读什么

1. 根目录 `AGENTS.md`
2. 被审查文件路径下最近层级的 `AGENTS.md`
3. PR / commit / diff 元信息、changed files、base/head、用户指定关注点
4. 关联 issue、OpenSpec change、设计文档、PRD、PR 评论和 CI 结果
5. 需要判断工程质量门槛时读 `.agents/skills/references/engineering-quality-gate.md`
6. 涉及 `apps/web/**` 时，先读 `.agents/skills/references/web-architecture-gate.md`；复杂 feature、route、shared 能力或文件拆分还要读 `.agents/skills/references/web-file-responsibility-and-feature-structure.md`；再读本 skill 的 Web review reference
7. 按变更路径加载本 skill 的 reference：
   - `apps/web/**`：读 `references/web/overview.md`
   - `apps/api/**`：读 `references/api/overview.md`
   - `packages/core/**`：读 `references/core/overview.md`
8. 需要统一输出格式时读 `references/shared/review-output.md`

不要一次性加载所有模块细则。先用 changed files、imports、调用形态和 diff 内容选择相关 reference。

## Review 流程

1. 明确审查对象：PR、commit range、单个 commit、工作区 diff，或用户粘贴的 patch。
2. 列出 changed files，并按路径和变更类型归类。
3. 读取相关真源和 overview reference，必要时再读未来的场景细则。
4. 对 diff 做证据驱动审查，只对能从当前代码、仓库规则、设计文档或验证结果证明的问题给 finding。
5. 如果建议来自通用最佳实践，但仓库真源没有支撑，标为 question / residual risk，不要写成 must-fix。
6. 对较新框架、库 API 或工具行为，先看 lockfile、已安装版本、现有代码和官方文档；不要只靠模型记忆。
7. 用普通 Markdown 输出 findings、open questions、验证建议和残余风险；需要贴到变更行的意见才使用 `::code-comment{...}`。

## Finding 分类

- `must-fix`：真实 bug、安全问题、契约破坏、仓库红线、关键测试缺口、会导致运行或审计失败的问题。
- `should-fix`：范围内、成本低、证据充分的质量问题。
- `needs-discussion`：会改变范围、设计、package 边界、OpenSpec、长期规则或验收口径的问题。
- `defer`：有价值但超出当前 PR，应进入后续 issue / change。
- `not-applicable`：通用建议不适用于当前仓库、当前版本、当前非目标或被现有设计明确排除。

不要因为发现“可以更好”就输出 finding。Code Review 优先报告会影响正确性、边界、安全、契约、可维护性或验证可信度的问题。

## 输出要求

默认输出普通 Markdown，不输出 JSON、XML、findings object 或其他结构化 review schema。

每条 finding 必须包含：

- 级别：`must-fix` / `should-fix` / `needs-discussion` / `defer` / `not-applicable`
- 文件和行号：尽量指向 diff 中最小可行动位置
- 规则来源：`AGENTS.md`、路径级 `AGENTS.md`、design、OpenSpec、issue、reference 或现有代码模式
- 证据：当前 diff 中触发问题的具体代码或行为
- 影响：为什么这会破坏仓库边界、行为、契约、安全或验证
- 建议修法：可执行的修改方向
- 验证建议：最小有效验证命令或人工检查点

如果没有 finding，明确说“未发现必须修改的问题”，并说明仍未覆盖的范围或未运行的验证。

只有当反馈需要直接贴到 changed line 时，才发出 `::code-comment{...}` inline comment 指令。没有可行动行级意见时，不要发任何 inline comment 指令。

## 关联 reference

- 输出格式：`references/shared/review-output.md`
- Web 规划与实现 gate：`.agents/skills/references/web-architecture-gate.md`
- Web 文件职责规范：`.agents/skills/references/web-file-responsibility-and-feature-structure.md`
- 前端管理台：`references/web/overview.md`
- FastAPI API 边界：`references/api/overview.md`
- 共享 core 包：`references/core/overview.md`

未来新增模块时，只在对应 overview 里加入导航，不把细则塞回 `SKILL.md`。

## 边界

- 本 skill 负责主动 review diff；处理已有 PR 评论、Copilot / CodeRabbit 评论或 CI 评论时优先使用 `gh-pr-comments`。
- 不自动修改代码，除非用户明确要求从 review 转入修复。
- 不接入 CI、GitHub bot 或自动阻塞 merge。
- 不把未确认想法写成仓库红线；需要长期沉淀时建议进入合适的 `AGENTS.md`、`docs/design/`、OpenSpec 或后续 issue。
