## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `plugin-io-dto-v1` 的 proposal、design、specs、tasks 和必要说明。
- [x] 1.2 在 PR 说明中写清楚：本 PR 只定义 Plugin IO DTO V1 contract，不实现 plugin-sdk / core runtime 代码，不接调度、入库或 Event Bus。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. DTO 契约

- [x] 2.1 定义 typed DTO 与 Runtime V1 通用 `PluginInvokeRequest` / `PluginInvokeResult` 的分层关系。
- [x] 2.2 定义 typed DTO 默认沿用冻结 `dataclass` 风格，但 contract 以字段语义、校验、序列化和只读行为为准。
- [x] 2.3 定义 typed DTO 不直接等同 ORM model、数据库对象或 core 内部 service 对象。
- [x] 2.4 定义 typed DTO 可校验、可序列化、可审计和脱敏的边界。

## 3. Source / Notification 第一版范围

- [x] 3.1 定义 `source.fetch` 第一版 typed input/output。
- [x] 3.2 定义中性 `SourceItemDraft` 命名，并明确不直接绑定 `RawEventDraft` / `EventDraft`。
- [x] 3.3 定义 `source.fetch` 的成功、有空结果和结构化失败场景。
- [x] 3.4 定义 `notification.send` 第一版 typed input/output，覆盖文本消息、`channel`、`severity` 和 metadata。
- [x] 3.5 定义 `notification.send` 的成功发送、上游失败和配置缺失场景。

## 4. 后续实现落点

- [x] 4.1 在 `packages/plugin-sdk` 中实现 typed DTO dataclass 与必要 helper，不重写 Runtime V1 transport。
- [x] 4.2 如需 runtime 挂接 helper，保持 helper / adapter 层完成 typed DTO 与 mapping 的互转，不在 runtime service 中写 capability 分支。
- [x] 4.3 为 source / notification typed DTO 增加最小 contract test 和序列化测试。

## 5. 验证

- [x] 5.1 运行 `openspec validate plugin-io-dto-v1 --type change --strict --json`。
- [x] 5.2 后续实现 PR 至少验证 typed DTO 可构造、可序列化、字段只读。
- [x] 5.3 后续实现 PR 至少验证 `source.fetch` 的成功、多 item、空结果和失败场景。
- [ ] 5.4 后续实现 PR 至少验证 `notification.send` 的成功、provider 拒收/限流 `accepted=false`、配置缺失、payload 校验失败、插件异常和 runtime 失败结构化错误场景。
