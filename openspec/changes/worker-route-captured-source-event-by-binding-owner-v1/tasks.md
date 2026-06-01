## 1. OpenSpec 评审与依赖确认

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `worker-route-captured-source-event-by-binding-owner-v1` 的 proposal、design、specs、tasks 和必要 PR 说明。
- [ ] 1.2 在 PR 说明中链接 issue #224，并写清本 PR 只收住 worker routing 契约，不进入 worker/core 实现。
- [ ] 1.3 在维护者明确评论“没问题”或批准前，不进入 `apps/worker/**`、`packages/core/**` 的实现代码。
- [ ] 1.4 在实现前复核 #217、#221、#226 是否继续复用 `binding_id` / `run_id` / owner 字段命名，不允许本 change 另起一套称谓。

## 2. captured 事件契约补齐

- [ ] 2.1 在 `packages/core/src/quantagent/core/events/` 规划 `source.event.captured` 的最小路由字段，至少稳定提供 `binding_id`、`request_id`、`plugin_id`、`message_id` 和 item 信息。
- [ ] 2.2 在 `scheduling-event-bus-bridge-v1` 的实现 PR 中补齐 `binding_id` 发布链路，并验证 worker 不需要按 `plugin_id` 反推 owner。
- [ ] 2.3 明确 `binding_id` 缺失时的受控失败语义与错误码，不能把缺字段视为可接受的降级路径。
- [ ] 2.4 在实现前按本 change 固定 `reason_code -> route_status -> consumer_disposition -> retryable -> audit_required` 映射，至少覆盖 binding 缺失、binding 不存在、binding 非 active、owner unsupported、duplicate、industry entrypoint failed 六类结果，避免 transport 层各自发明口径。

## 3. worker/core 目录与分层实现

- [ ] 3.1 在 `apps/worker/src/quantagent/worker/consumer/` 新增 captured event handler，只负责订阅 topic、解码 envelope、调用 routing service。
- [ ] 3.2 在 `packages/core/src/quantagent/core/worker_routing/` 新增 `models.py`、`captured_event_decoder.py`、`service.py`、`owner_resolver.py`、`industry_gateway.py` 和 `README.md`，按职责拆分而不是堆进一个文件。
- [ ] 3.3 在 `service.py` 中实现 `SourceBinding` 查询、状态过滤、owner 解析、duplicate 处理和行业入口调用编排，并补必要中文注释说明幂等 / 失败隔离原因。
- [ ] 3.4 在 `owner_resolver.py` 中明确 V1 只支持 `owner_type == "industry"` 的成功路径，其余 owner 返回结构化 unsupported 结果。
- [ ] 3.5 在 `industry_gateway.py` 中保持受控入口 seam，不直接 import 具体行业插件实现列表或写硬编码 if/else 注册。
- [ ] 3.6 将 `industry_gateway.py` 实现为 core port；V1 即使先接 fake / no-op adapter，也必须返回结构化 `IndustryGatewayResult`，禁止直接透传插件私有返回值或异常字符串。

## 4. 失败路径与最小测试

- [ ] 4.1 在 `packages/core/tests/test_worker_captured_event_routing.py` 覆盖成功路由到 industry owner 的最小路径。
- [ ] 4.2 覆盖 `binding_id` 缺失、binding 不存在、binding 非 active、owner 不支持、duplicate message 五类受控结果。
- [ ] 4.3 覆盖下游行业入口失败时的结构化失败与审计上下文字段断言。
- [ ] 4.4 覆盖 `reason_code -> route_status -> consumer_disposition -> retryable -> audit_required` 映射断言，确保六类结果不会在实现时漂移。
- [ ] 4.5 在 `apps/worker/src/tests/` 增加 composition root 级测试，确认 worker 只负责组装 consumer/runtime，不内嵌行业业务。

## 5. 验证与协作边界

- [ ] 5.1 运行 `openspec validate worker-route-captured-source-event-by-binding-owner-v1 --type change --strict --json`。
- [ ] 5.2 后续实现 PR 至少验证 worker routing 结果不会退化为按 `plugin_id` 分发。
- [ ] 5.3 后续实现 PR 说明中必须写清与 #217 的协作方式：#217 负责生产带 `binding_id` 的 captured 事件，#224 负责消费并路由。
- [ ] 5.4 后续实现 PR 说明中必须写清与 #221 的协作方式：#221 负责 RawEvent 持久化 / dedupe 真源，#224 只复用 `binding_id` 与 duplicate 语义，不跨界实现 RawEvent。
