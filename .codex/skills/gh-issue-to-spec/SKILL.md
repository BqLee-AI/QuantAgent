---
name: gh-issue-to-spec
description: Use when the user wants Codex to convert a GitHub issue into a durable repository spec before implementation. Applies when picking up an issue, turning issue requirements into OpenSpec/ADR/RFC/design docs, clarifying scope from an issue, producing proposal/design/tasks artifacts, or preparing an issue for human review before coding. This skill reads the issue with gh, follows the repository's existing spec system, writes or updates spec artifacts, and stops for approval before implementation.
---

# GitHub Issue To Spec

这个 skill 用于把 GitHub issue 转成可审核、可长期保存的 spec 资产。它不是“读完 issue 直接写代码”的流程；目标是先把问题定义、边界、验收、未决点和任务图落到仓库文件里。

## 目标仓库和 issue

优先从用户输入获取 issue 编号、URL 或 `owner/repo#number`。如果只给了编号，默认使用当前 git 仓库。

先确认仓库：

```bash
git remote -v
gh repo view --json nameWithOwner,url
```

读取 issue：

```bash
gh issue view ISSUE --repo OWNER/REPO --json number,title,body,labels,url,state,assignees,milestone,comments
```

如果无法确定 issue 或仓库，先问一个聚焦问题。不要在 issue 本体没读到时编写 spec。

## 只读必要上下文

开始前，只读取当前 issue 真正需要的上下文：

- 协作规则：`AGENTS.md`、`README.md`、`CONTRIBUTING.md`
- issue 模板或开发工作流说明：`.github/ISSUE_TEMPLATE/`
- 仓库现有 spec 体系：`docs/openspec/`、`openspec/`、`specs/`、`docs/specs/`、`docs/adr/`、`adr/`、`rfcs/`、`docs/rfcs/`
- issue 正文或评论中点名的 PR、discussion、文档、任务、日志、测试、代码文件
- 如果仓库有 OpenSpec 指南或已有 change 示例，只读取最接近当前 issue 的示例

不要批量扫描整个仓库。先定位现有约定，再按约定落文件。

## 判断是否可转成 spec

先从 issue 中提炼：

- 单一问题定义
- 背景 / 为什么现在做
- 目标
- 非目标
- 已知上下文
- 依赖或阻塞项
- 未决问题
- 验收口径
- 必要验证

如果 issue 是一包大功能或多个独立问题，不要直接写成一个大 spec。先拆成建议的 spec/issue 边界，征求用户确认。

如果关键边界模糊，先问 1-3 个会改变 spec 结构的问题；不要问低价值偏好题。

## 选择 spec 形态

遵循仓库已有体系，优先级如下：

1. 如果仓库已有 OpenSpec/change 结构，创建或更新对应 change 目录。
2. 如果仓库已有 ADR/RFC/design doc 体系，按其命名和模板创建文档。
3. 如果只有轻量 specs 目录，创建一个单文件 spec。
4. 如果没有任何体系，创建最小持久化 spec，默认放在 `docs/specs/`。

不要为了使用某个固定格式而破坏项目已有约定。

## OpenSpec 形态

如果仓库使用 OpenSpec 或类似 change 包，优先产出：

```text
<spec-root>/changes/<change-id>/
├── proposal.md
├── design.md        # 需要设计细节时才创建
└── tasks.md
```

`change-id` 使用短动词短语，来自 issue 目标，例如 `add-login-rate-limit`。避免只用 `issue-123`，但可以在文件中链接 issue。

`proposal.md` 至少包含：

- Issue 链接
- 背景 / 为什么现在做
- 问题定义
- 目标
- 非目标
- 影响范围
- 依赖和风险
- 未决问题
- 验收口径

`design.md` 只在实现路径、接口、数据模型、迁移、兼容性或安全边界需要被审核时创建。不要为简单文档或小修补硬造设计文档。

`tasks.md` 必须表达依赖关系，而不是只有线性待办。

## 单文件 spec 形态

如果仓库没有 change 包约定，创建单文件 spec：

```markdown
# <issue title derived spec title>

## Source

- GitHub issue: <url>
- Labels:
- State:

## Background

## Problem

## Goals

## Non-Goals

## Scope

## Known Context

## Dependencies

## Open Questions

## Acceptance

- Must hold:
- Explicitly not required:
- Failure signals:

## Task Graph

### Blocking Path

### Parallelizable Work

### Review Points

## Verification
```

正文语言跟随用户请求或仓库既有 spec 风格。

## tasks 必须是任务图

任务不能写成“先做 A、再做 B、再做 C”的普通施工清单。必须区分：

- 串行阻塞项：不先完成会导致后续方向漂移
- 可并行项：写入边界不冲突、输入输出清楚
- 审核点：哪些完成后需要用户或维护者再看 spec / 结果
- 每个任务的输入、输出和写入边界

推荐格式：

```markdown
## Task Graph

### Blocking Path

- [ ] B1. <task>
  - Input:
  - Output:
  - Write boundary:

### Parallelizable Work

- [ ] P1. <task>
  - Can start after:
  - Input:
  - Output:
  - Write boundary:

### Review Points

- [ ] R1. Review <artifact/result> before implementation continues.
```

## 审核门槛

写入 spec 后必须停下，向用户返回：

- spec 文件路径
- 从 issue 提炼出的核心问题定义
- 目标和非目标摘要
- 未决问题
- 任务图摘要
- 是否建议进入实现

在用户明确批准前，不要实现代码，不要修改无关文件，不要把 tasks 往前推进。

如果用户明确只要求“生成 spec，不实现”，完成 spec 后直接收口。

## 与实现阶段的关系

如果用户之后批准实现：

- 重新读取已落地的 spec，而不是只依赖聊天摘要。
- 用计划跟踪机制把任务图转成执行计划。
- 先处理阻塞路径。
- 可并行任务只有在写入边界清晰且互不重叠时才拆给子 Agent。
- 实现完成后同步更新 spec/tasks 状态，记录验证结果。

这个 skill 的默认结束点是 spec 审核，不是代码实现。

## 护栏

- 不要跳过 issue 读取。
- 不要把聊天摘要当成 spec 交付物。
- 不要把多个独立问题塞进一个 spec。
- 不要忽略 issue 里的非目标和未决点。
- 不要在没有审核前直接实现。
- 不要把任务写成没有依赖关系、没有写入边界的清单。
- 不要假设所有仓库都使用 OpenSpec；先看本仓库约定。
- 不要创建与仓库现有 spec 体系冲突的新目录，除非仓库没有任何约定。

## 完成后返回

至少返回：

- issue 标题和 URL
- 产出的 spec 路径
- 问题定义
- 关键目标 / 非目标
- 未决问题
- 审核状态：等待用户审核、需要补充信息，或已批准进入实现
