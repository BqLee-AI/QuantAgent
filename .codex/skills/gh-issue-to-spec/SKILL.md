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

如果关键边界模糊，使用结构化提问协议：

1. **只问会改变 spec 结构的问题**：如果答案不会影响 proposal.md 的目标/非目标/范围划分，或不会改变 tasks.md 的依赖关系，不要问。
2. **最多 3 个问题**：一次提问不超过 3 个，按影响面从大到小排列。先问清楚会改变整个 spec 方向的问题。
3. **提供默认建议**：每个问题附带一个合理默认值，用户可以快速确认而不是从零思考。例如："401 恢复策略默认用 cookie session refresh，是否需要支持其他方式？"
4. **不要问偏好题**：命名风格、文件组织方式、注释密度等低价值偏好不作为阻塞问题。

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

**与 OpenSpec 的兼容**：当仓库使用 OpenSpec change 包结构时，tasks.md 即为 change 目录下的 `tasks.md`。上述 Task Graph 格式直接写入该文件，不需要额外转换。每个 checkbox 对应 OpenSpec tasks 中的一个待办项，实现完成后直接在文件中勾选。

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

1. **重新读取 spec**：从磁盘重新读取已落地的 spec 文件（proposal.md、design.md、tasks.md），不依赖聊天上下文中的摘要。
2. **任务图 → 执行计划**：将 tasks.md 中的任务图转为执行计划，使用计划跟踪机制。
3. **执行顺序**：
   - 先处理阻塞路径（Blocking Path），后续任务的正确性依赖前置任务完成。
   - 可并行任务（Parallelizable Work）只有在写入边界清晰且互不重叠时才拆给子 Agent 并行执行。
4. **审核点触发**：遇到 Review Point 时暂停，将中间结果展示给用户确认后再继续。
5. **状态同步**：每个任务完成后，立即在 tasks.md 中勾选对应 checkbox。发现 spec 与实际实现有偏差时，回写 spec 而不是静默偏离。
6. **验证闭环**：实现完成后，运行 tasks.md §8（Verification）中的所有检查项。将验证结果记录到 spec 或 PR description 中。

这个 skill 的默认结束点是 spec 审核，不是代码实现。实现阶段的启动需要用户明确批准。

## 护栏

- 不要跳过 issue 读取。
- 不要把聊天摘要当成 spec 交付物。
- 不要把多个独立问题塞进一个 spec。
- 不要忽略 issue 里的非目标和未决点。
- 不要在没有审核前直接实现。
- 不要把任务写成没有依赖关系、没有写入边界的清单。
- 不要假设所有仓库都使用 OpenSpec；先看本仓库约定。
- 不要创建与仓库现有 spec 体系冲突的新目录，除非仓库没有任何约定。

## 实现后验证清单

如果用户批准实现且实现完成后，运行以下验证：

1. **Spec 一致性**：实际代码实现是否与 proposal.md 中的目标和范围一致。如有偏差，spec 是否已同步更新。
2. **Tasks 完成度**：tasks.md 中所有 checkbox 是否已勾选。未勾选项是否有说明（如标记为后续 issue）。
3. **构建通过**：`bun run build` 或仓库等效构建命令通过。
4. **测试通过**：tasks.md 中声明的验证项是否全部执行且通过。
5. **未决问题闭环**：proposal.md 中的 Open Questions 是否都已解决或转为新的 issue。
6. **文件写入边界**：实际修改的文件是否在 tasks.md 声明的写入边界内，有无越界修改。

## 完成后返回

至少返回：

- issue 标题和 URL
- 产出的 spec 路径
- 问题定义
- 关键目标 / 非目标
- 未决问题
- 审核状态：等待用户审核、需要补充信息，或已批准进入实现
