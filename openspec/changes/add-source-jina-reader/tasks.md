## 1. Plugin Contract Gate

- [ ] 1.1 固定 `Jina Reader` 的插件包边界：只做 `source/read`，不做 `tool.read_url`。
- [ ] 1.2 固定插件输出贴齐平台约定的 Source Plugin 输出结构，不新增 reader 专用 DTO，也不在本 change 中绑定 core 内部 DTO 名称。
- [ ] 1.3 固定插件不负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限和生命周期。

## 2. External Reader Boundary Gate

- [ ] 2.1 固定插件公开最小配置字段集合：`url`、可选非敏感请求参数和超时控制，不暴露原始外部 reader 鉴权字段。
- [ ] 2.2 记录“外部 reader 鉴权由平台统一控制”的边界，不把真实 token / 私有账号写入插件公开 schema。
- [ ] 2.3 明确是否允许外发 URL 由平台策略结果传入插件，插件只遵循允许/禁止外发边界并清晰拒绝不允许外发的请求。
- [ ] 2.4 明确外部 reader 限流、超时或服务失败时，本轮只要求清晰失败返回，不引入自动 fallback 编排。

## 3. Verification Gate

- [ ] 3.1 约定最小交付物：`plugin.yaml`、`config.schema.json`、README、入口实现、最小测试。
- [ ] 3.2 约定最小验证优先使用 mock / fixture / 受控响应，不依赖真实外部服务稳定性。
- [ ] 3.3 运行 `openspec validate add-source-jina-reader --type change --strict --json`。
- [ ] 3.4 基于本 change 创建 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入实现。
