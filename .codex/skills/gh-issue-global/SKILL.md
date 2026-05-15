---
name: gh-issue-global
description: Use when the user wants Codex to draft, create, refine, or batch-create GitHub issues in any repository using the gh CLI. Applies to development tasks, bugs, feature requests, documentation work, maintenance work, and issue triage. Guides Codex to gather local repo context, follow repository issue templates and label conventions, write scoped issue bodies, create issues non-interactively, and verify the created issue and labels.
---

# GitHub Issue Global

这个 skill 用于把粗略需求、代码上下文、讨论记录、规格文档或待办项转成可接手的 GitHub issue。默认面向当前本地仓库，也可以按用户指定的 `owner/repo` 创建。

## 核心立场

每一个创建的 issue 必须是一个 **可独立接手、可独立验收的工作单元**。不是需求转储，不是备忘录，不是讨论帖。如果原始输入包含多个独立问题，先拆分再创建，不要糊成一个大 issue。issue 的边界、验收口径和未决问题必须在创建前想清楚，而不是留给接手者脑补。

## 先确认目标仓库

优先从当前 git 仓库推断远端：

```bash
git remote -v
gh repo view --json nameWithOwner,url
```

如果用户指定了仓库，使用用户指定值。若无法可靠判断仓库，先问一个聚焦问题：issue 要创建到哪个 `owner/repo`。

创建前确认 `gh` 可用且已认证：

```bash
gh auth status
```

不要在未确认目标仓库时创建 issue。

## 只读必要上下文

开始起草前，只读取当前任务真正需要的上下文：

- 仓库协作说明：`AGENTS.md`、`CONTRIBUTING.md`、`README.md`
- issue 模板：`.github/ISSUE_TEMPLATE/` 下相关模板、`config.yml`
- 标签定义：`.github/labels.yml`、`.github/labels.yaml` 或其他本仓库实际使用的标签说明
- 用户点名的规格、设计、任务、讨论、日志、测试失败输出或代码位置
- 对 bug issue，读取复现路径、相关测试、错误日志和可疑代码
- 对批量 issue，读取能说明拆分边界的计划文档或任务列表

不要批量读取无关文件。没有模板时使用下方通用正文结构。

## 创建前检查

创建 issue 前，先确认能回答这些问题：

1. 这个 issue 收住的单一问题是什么。
2. 为什么现在需要处理它，影响或阻塞是什么。
3. 本 issue 解决什么，明确不解决什么。
4. 接手者需要知道哪些现有上下文、链接、文件或命令。
5. 验收口径是什么，哪些结果算没有完成。
6. 还有哪些问题不能由实现者擅自脑补。

如果关键点仍然模糊，只能做两件事之一：

- 问用户一个聚焦的收窄问题。
- 或先起草 issue body，不创建远端 issue，并明确标记为需要确认。

不要硬造一个看起来完整、实际没有边界的 issue。

## 正文写法

优先遵循仓库自己的 issue 模板。模板字段必须有实质内容；不适用的字段写清为什么不适用，不要留空。

没有模板时，使用这个结构：

```markdown
## 背景 / 为什么现在做

说明触发背景、影响范围、当前阻塞或漂移风险。

## 当前问题

点名需要收住的单一问题。bug issue 要包含观察到的行为和期望行为。

## 本 issue 想解决什么

- 明确边界 1
- 明确边界 2
- 明确边界 3

## 明确不解决什么

- 本次不进入的范围
- 需要后续 issue 或决策处理的内容

## 已知上下文

- 相关文件、命令、日志、PR、discussion、规格文档或已有 issue

## 前置依赖

说明是否被阻塞；如未被阻塞，写“暂无明确前置依赖”。

## 需要确认的问题

- 接手前必须确认的问题；没有则写“暂无”。

## 子任务

- [ ] 子任务 1
- [ ] 子任务 2
- [ ] 子任务 3

## 验收口径

- 必须成立：
- 明确不要求：
- 失败信号：

## 验证要求

分层列出验证项，与风险级别匹配：

- **必须通过**（阻塞合并）：typecheck、lint、核心路径单测
- **应当通过**（本 issue 范围内完成）：功能相关的集成测试、边界用例
- **可后续补充**（不阻塞本 issue 关闭）：浏览器集成测试、性能回归、可访问性检查

不要把重型验证提前塞进低风险 issue。验证的深度应与改动的影响范围成正比。
```

正文默认使用用户语言；如果仓库既有 issue 都使用另一种语言，跟随仓库风格。

## 标签规则

标签必须来自仓库现有约定，而不是只凭 GitHub 默认标签。

创建前检查：

```bash
gh label list --repo OWNER/REPO --limit 200
```

如果仓库有 `.github/labels.yml` 或同类标签定义，优先以仓库定义为准。若定义中的必要标签尚未同步到远端，先征得用户同意再创建或更新远端标签；不要擅自改动大型标签体系。

通用最小标签策略：

- 有 `type:*` / `kind:*` / `category:*` 体系时，选择一个最贴近的类型标签。
- 有 `priority:*` 体系时，默认 `priority:medium`，阻塞关键路径才用 high，不在近期路径才用 low。
- 有 `status:*` 体系时，新建默认用表示待确认的状态，例如 `status:needs-review`；只有边界、验收、依赖都清楚时才用 ready。
- 有 `area:*` / `component:*` 体系且影响范围明确时，补充对应范围标签。

如果仓库没有明确标签体系，使用最少且准确的现有默认标签，例如 `bug`、`enhancement`、`documentation`。不要为了显得完整而创建新标签。

## gh 命令模式

优先使用非交互式 `gh` 命令。

1. 将正文写入临时 markdown 文件。
2. 使用显式 `--repo`、`--title`、`--body-file`、`--label` 创建 issue。
3. 创建后立即回读 issue，核对标题、URL、正文摘要和标签。
4. 如果标签缺失或挂错，在确认仓库标签存在后用 `gh issue edit` 修正。
5. 标签验证：对比实际挂载的标签与预期标签列表。如果 GitHub 静默忽略了不存在的标签（`gh issue create` 对无效 `--label` 不报错），必须用 `gh issue view --json labels` 的输出来确认标签已正确挂载，缺失的标签用 `gh issue edit` 补挂。

示例：

```bash
gh issue create \
  --repo OWNER/REPO \
  --title "feat(scope): 简短中文描述" \
  --body-file issue.md \
  --label enhancement \
  --label priority:medium

gh issue view NUMBER --repo OWNER/REPO --json number,title,url,labels,state
```

批量创建时先生成每个 issue 的标题、范围、标签和依赖关系清单；除非用户明确授权，先给用户审阅清单，再逐个创建。

## 护栏

- 不要把多个独立架构决策、bug、功能点糊成一个大 issue。
- 不要把任务标题直接变成 issue，而不补背景、非目标和验收。
- 不要写“基本可用”“支持扩展”“优化体验”这类空洞验收。
- 不要在关键未决点存在时标记为 ready。
- 不要把重型验证提前塞进不需要它的 issue；验证要求应与风险匹配。
- 不要创建完 issue 后不回读结果。
- 不要未经用户许可创建或批量修改远端标签。

## 完成后返回

创建完成后，返回：

- issue 标题
- issue URL
- label 集合
- 当前状态：可直接接手、等待 review、被依赖阻塞，或仍需用户确认

如果只起草未创建，返回草稿文件路径、建议标题、建议标签和还缺的确认点。
