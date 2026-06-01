## 1. OpenSpec 评审

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `raw-event-persistence-dedupe-binding-v1` 的 proposal、design、tasks、specs 和必要说明。
- [ ] 1.2 在 PR 说明中链接 #221，并明确这是补齐缺失的 RawEvent OpenSpec-only PR，不进入实现代码。
- [ ] 1.3 在 PR 说明中写清楚与 PR #250 的关系：#250 后续实现必须对齐本 change，再继续收敛代码与验证。
- [ ] 1.4 等维护者明确评论“没问题”或批准后，再推进后续实现 PR。

## 2. 持久化模型蓝图

- [ ] 2.1 在 OpenSpec 中固定 `raw_events` canonical 主表与 `raw_event_captures` append-only ownership 表的双层模型。
- [ ] 2.2 固定 canonical RawEvent 的最小字段：`raw_event_id`、`source_plugin_id`、`canonical_dedupe_key`、`dedupe_strategy`、`external_id`、`canonical_url`、`content_hash`、结构化内容字段、`raw_payload`、`first_binding_id`、`first_run_id`、`duplicate_capture_count`。
- [ ] 2.3 固定 capture row 的最小字段：`capture_id`、`raw_event_id`、`binding_id`、`run_id`、`capture_status`、`captured_at`、`request_id` 和最小 metadata。
- [ ] 2.4 固定 ownership 语义：跨 binding / run duplicate 复用 canonical row，但必须追加新的 capture row。

## 3. Dedupe 与并发语义

- [ ] 3.1 固定 dedupe 作用域为 `source_plugin_id` 内，不按 binding 或 run 切分 canonical identity。
- [ ] 3.2 固定 dedupe 优先级：`external_id` -> `canonical_url + content_hash` -> `provider_dedupe_hint`。
- [ ] 3.3 固定 canonical 唯一键与 capture 幂等唯一键的存在性要求，避免先查后写 race condition。
- [ ] 3.4 固定并发 duplicate upsert、唯一键冲突后重读和同 run 幂等重试的事务语义。

## 4. Payload 与安全边界

- [ ] 4.1 固定 `raw_payload` 只保存 replay/debug 必需的 provider-native JSON-safe 字段，不保存 secret、cookie、auth header、完整 HTML、二进制附件或宿主对象。
- [ ] 4.2 固定高价值字段必须结构化落表，不允许只藏在 `raw_payload`。
- [ ] 4.3 固定 `raw_payload` 128 KiB 上限，以及裁剪或拒绝写入时的审计标记要求。
- [ ] 4.4 固定失败摘要和 payload 裁剪行为必须脱敏，不暴露绝对路径、token 或未遮盖 query 参数。

## 5. 相邻 change 与后续实现对齐

- [ ] 5.1 明确复用 `source-binding-scheduler-run-persistence-v1` 的 `binding_id` / `run_id` 命名，不重新发明字段。
- [ ] 5.2 明确 #217 scheduler loop 未来只能通过 `RawEventService` 写入 RawEvent，不得自己重算 dedupe 或直接写 ORM。
- [ ] 5.3 明确 #250 后续实现应把 duplicate summary 与 ownership ledger 分开，不能只保留 canonical row + duplicate_count。
- [ ] 5.4 明确 future Event 标准化只消费 canonical RawEvent 与 capture ownership 引用，不反向修改 dedupe 规则。

## 6. 验证

- [ ] 6.1 运行 `openspec validate raw-event-persistence-dedupe-binding-v1 --type change --strict --json`。
- [ ] 6.2 后续实现 PR 至少在 PostgreSQL 上验证 canonical 唯一约束、capture 幂等唯一约束和冲突后重读语义。
- [ ] 6.3 后续实现 PR 至少验证跨 binding duplicate 会新增 capture row，但不会新增第二条 canonical RawEvent。
- [ ] 6.4 后续实现 PR 至少验证同一 `run_id` 的 DB 重试不会生成重复 capture row。
- [ ] 6.5 后续实现 PR 至少验证超限或敏感 `raw_payload` 会被裁剪或拒绝，并留下脱敏审计标记。
- [ ] 6.6 SQLite 可作为补充单测，但不得作为本 change 的唯一数据库验收口径；PR 说明必须明确 PostgreSQL 验证结果。
