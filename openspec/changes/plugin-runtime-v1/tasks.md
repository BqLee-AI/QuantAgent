## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含本 change 的 proposal、design、specs、tasks 和必要说明。
- [x] 1.2 在 PR 说明中写清楚：本 PR 只定义 Plugin Runtime V1 契约，不实现代码、不接调度链路、不接真实交易执行。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. Runtime 契约

- [x] 2.1 定义 Runtime 从 Registry 有效记录加载 manifest entrypoint 的行为。
- [x] 2.2 定义 entrypoint 加载失败、无效插件记录和 capability 不存在时的结构化错误。
- [x] 2.3 定义 RuntimeContext 最小字段和禁止暴露的宿主内部对象。
- [x] 2.4 定义配置注入方式：平台传入已校验 config DTO / effective config，插件不自行读取配置真源。

## 3. Plugin SDK 最小面

- [x] 3.1 在 `packages/plugin-sdk` 中实现 RuntimeContext、invoke request/result、health check result 和结构化错误类型。
- [x] 3.2 实现 RuntimePlugin Protocol，用于描述 Runtime 需要调用的生命周期与统一 invoke 能力。
- [x] 3.3 实现轻量可选 `BasePlugin`，提供默认 lifecycle、保存 context、logger 访问和错误辅助。
- [x] 3.4 确保 Runtime 不以 `isinstance(plugin, BasePlugin)` 作为唯一接收条件。

## 4. Core Runtime 最小实现

- [x] 4.1 在 core runtime 落位实现插件 loader / runtime service，不把加载逻辑写进 API router。
- [x] 4.2 实现 `load`、`start`、`health_check`、`stop` 的调用顺序和失败包装。
- [x] 4.3 实现统一 invoke 调用和结果校验。
- [x] 4.4 确保 RuntimeContext 不暴露 DB session、ORM model、scheduler、Event Bus publisher 或内部 service。

## 5. 验证

- [x] 5.1 添加 contract test：可加载满足协议但未继承 BasePlugin 的插件对象。
- [x] 5.2 添加 contract test：可加载继承 BasePlugin 的插件对象，并验证默认 lifecycle 行为。
- [x] 5.3 添加测试覆盖 entrypoint 加载失败。
- [x] 5.4 添加测试覆盖配置注入。
- [x] 5.5 添加测试覆盖插件 invoke 抛错或返回非法结果时的结构化错误。
- [x] 5.6 添加测试覆盖 RuntimeContext 不暴露禁止的宿主内部对象。
- [x] 5.7 运行 `openspec validate plugin-runtime-v1 --type change --strict --json`。
