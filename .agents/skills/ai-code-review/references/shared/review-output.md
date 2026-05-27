# Review 输出规范

本文件定义 `ai-code-review` 的统一输出格式。模块 reference 只补充模块规则，不重复定义输出结构。

## 基本格式

Review 回复使用普通 Markdown。不要返回 JSON、XML、findings object 或其他结构化 review schema。

当反馈应该直接贴到变更行时，发出一个 `::code-comment{...}` 指令；没有可行动行级意见时不要发该指令。指令必须包含 `title`、`body`、`file`，可选 `start`、`end`、`priority`。行号范围使用最短有用范围，`file` 使用绝对路径或包含 workspace 片段的路径。

可见回复仍保持普通 Markdown；inline comment 指令只用于需要贴到 changed line 的离散问题。

## Findings 优先

Code Review 回复先列 findings，按严重度排序。不要先写长摘要。

每条 finding 使用这个结构：

```markdown
- [must-fix] `path/to/file.ts:42` 标题
  - 规则来源：`apps/web/AGENTS.md` / `references/web/overview.md`
  - 证据：diff 中的具体调用或行为
  - 影响：为什么它会破坏边界、契约、安全或验证
  - 建议：最小可执行修法
  - 验证：建议运行的命令或人工检查点
```

如果平台支持 inline comment，可把同样信息压缩成行级评论，但仍要保留规则来源和影响说明。

## 报告门槛

只报告同时满足这些条件的问题：

- 明显影响正确性、性能、安全或可维护性。
- 离散、可定位、可行动。
- 由当前变更引入或暴露。
- 作者知道后大概率会修。
- 不依赖未声明的意图假设。
- 能清楚说明受影响行为，而不是泛泛推测。

宁可不报，也不要输出低信号、猜测性或偏好型意见。

## 分类语义

- `must-fix`：不修会产生真实风险，或违反仓库硬规则。
- `should-fix`：建议在当前 PR 内修，证据充分且成本可控。
- `needs-discussion`：需要维护者拍板，不能由 reviewer 自行改范围。
- `defer`：放入后续 issue，不阻塞当前 PR。
- `not-applicable`：说明为什么某条通用建议不适用。

## 收口信息

findings 后补充：

- 已加载的 reference
- 未覆盖的路径或模块
- 已运行或建议运行的验证
- 残余风险和 open questions

如果没有 finding，仍需说明：

- 审查了哪些 changed files
- 加载了哪些 reference
- 哪些验证没有运行
- 是否存在 residual risk

如果没有可行动问题，直接简短说明“未发现可行动问题”。

## 禁止输出

- 不输出无法定位到文件、规则或证据的泛泛建议。
- 不把个人偏好写成 `must-fix`。
- 不复制大段 diff 或源码。
- 不用“最佳实践”替代仓库真源。
- 不为无法贴到 changed line 的总结性意见创建 `::code-comment{...}`。
