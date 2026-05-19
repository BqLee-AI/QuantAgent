# PR Body 模板

```markdown
## 关联

- Issue:
- OpenSpec change:

## 背景

## 改动

## 验证

## 风险与未验证项

## Review Notes
```

## 写法

- `关联` 写 issue URL、change id、相关 PR 评论或设计文档段落。
- `背景` 写这次 PR 为什么这样改，不重复粘贴完整 issue。
- `改动` 按 API / Web / Core / OpenSpec / Docs 等边界组织。
- `验证` 写实际运行的命令和结果；失败或跳过要写原因。
- `风险与未验证项` 写 review 需要关注的残余风险。
- `Review Notes` 预先解释容易被 AI review 误判的点，例如新版本 API、非目标、刻意不做的抽象。

## AI Review 预防性说明

如果使用较新的技术栈或本仓库已有局部约定，PR body 应写明依据：

- 当前 lockfile / package version。
- 官方文档或现有代码模式。
- 为什么没有采用 AI 可能建议的旧 API、过度抽象或通用最佳实践。

这样不是为了防御 review，而是让 reviewer 更快判断建议是否适用于当前项目。
