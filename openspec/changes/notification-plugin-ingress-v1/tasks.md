## 1. OpenSpec 评审

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `notification-plugin-ingress-v1` 的 proposal、design、specs、tasks 和必要说明。
- [ ] 1.2 在 PR 说明中写清楚：本 change 先收住 notification ingress / receive DTO / orchestration 边界，不直接实现完整审批、聊天会话或多渠道全量功能。
- [ ] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. Plugin SDK

- [x] 2.1 在 `packages/plugin-sdk` 新增 `NotificationReceiveInput` typed DTO，字段覆盖 `transport`、`headers`、`body_text` / `body_base64`、`query_params`、`path_params`、`request_metadata` 和可选 `config_override`。
- [x] 2.2 保持 `NotificationReceiveInput` 与现有 DTO 一致的 JSON-safe、只读和冻结语义。
- [x] 2.3 为 `NotificationReceiveInput` 增加最小 roundtrip / validation tests，不依赖 FastAPI。
- [x] 2.4 如需要兼容旧的 ad hoc mapping，提供最小 adapter/helper，而不是在 runtime service 中写 capability 特例分支。

## 3. Core Orchestration

- [x] 3.1 在 `packages/core` 设计并实现平台侧 `NotificationIngressService` 或等价 orchestration 边界。
- [x] 3.2 由 core orchestration 负责 plugin record 校验、runtime invoke、result 校验和标准化返回。
- [ ] 3.3 定义 notification receive record / audit 的最小 service 边界；实现阶段可先用内存或轻量 seam，不要求一步到位落数据库。
- [ ] 3.4 明确 topic 发布边界：如果第一版引入 `notification.received`，只能由平台 orchestration 发布，插件不得直接 publish。
- [x] 3.5 为 orchestration 补最小单元测试，覆盖 plugin 不存在、capability 缺失、runtime 失败、receive result 非法、成功返回 item 等场景。

## 4. API Host 收敛

- [x] 4.1 在 `apps/api` 引入通用 notification ingress host 调用方式，不再让 Discord 专属 service 成为长期编排真源。
- [x] 4.2 删除 Discord 公共 route 形状与专属 service，统一收敛到通用 ingress orchestration。
- [x] 4.3 把 Discord-specific settings 的长期职责从 API 私有编排中收缩，避免继续扩展宿主特例。
- [x] 4.4 为 API 层补测试，验证 request body / headers 能正确转换为 `NotificationReceiveInput` 并传入 orchestration。

## 5. 多 transport 扩展边界

- [x] 5.1 在实现注释和 README/设计说明中明确：Notification Plugin Ingress V1 的模型需要兼容 webhook、websocket、polling 三类 transport。
- [x] 5.2 本轮实现严格限制在 Discord 所需的 HTTP host adapter，不实现 websocket host 或 polling host。
- [x] 5.3 确保 `NotificationReceiveInput.transport` 和 orchestration 设计不会把模型钉死在 HTTP-only 语义上。

## 6. Discord 样板改造

- [x] 5.1 更新 Discord 插件实现，使 receive 路径消费新的 `NotificationReceiveInput`，而不是继续依赖 ad hoc `headers` / `body` mapping。
- [x] 5.2 保持 Discord 插件内部继续负责验签、`PING`、最小 command payload 解析和 response 生成。
- [x] 5.3 更新 Discord README、smoke 和测试，明确它是 Notification Plugin Ingress V1 的样板实现。
- [x] 5.4 确保 Discord 插件不直接发布 Event Bus、写审批记录或推进业务状态。

## 7. 后续主链衔接

- [x] 6.1 明确 receive result 成功后如何进入 receive record / audit / approval handoff 的下一步 change。
- [ ] 6.2 如本轮不直接做持久化，至少在实现 PR 说明中写清楚 residual risk：receive 结果仍未成为持久化真源。
- [ ] 6.3 后续独立 change 再决定是否引入 `notification.received` stable topic、数据库持久化和完整审批回流。
