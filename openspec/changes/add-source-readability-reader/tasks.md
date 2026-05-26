## 1. Plugin Contract Gate

- [ ] 1.1 固定 `Readability Link Reader` 的插件包边界：只做 `source/read`，不做 `tool.read_url`。
- [ ] 1.2 固定插件输出贴齐平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO，不新增 reader 专用 DTO。
- [ ] 1.3 固定插件不负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限和生命周期。

## 2. Config And Dependency Gate

- [ ] 2.1 固定最小配置字段集合：`url`、可选 `headers`、`timeout_seconds` 和必要抽取参数。
- [ ] 2.2 记录“允许插件内部封装成熟 Python 开源正文抽取库”的依赖策略。
- [ ] 2.3 明确该依赖属于插件实现细节，不改变 core / API / web 的依赖边界。

## 3. Verification Gate

- [ ] 3.1 约定最小交付物：`plugin.yaml`、`config.schema.json`、README、入口实现、最小测试。
- [ ] 3.2 约定最小验证优先使用静态 HTML fixture 或受控输入，不依赖真实外部站点稳定性。
- [ ] 3.3 运行 `openspec validate add-source-readability-reader --type change --strict --json`。
- [ ] 3.4 基于本 change 创建 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入实现。
