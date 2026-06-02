## 1. OpenSpec 评审门槛

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `ai-event-intake-single-call-routing-v1` 的 proposal、design、specs、tasks 和必要说明。
- [ ] 1.2 在 PR 说明中链接 issue #266，并写清本 PR 只收住单次 AI intake / routing 契约，不进入实现代码。
- [x] 1.3 在维护者明确评论“没问题”或批准前，不进入 `apps/worker/**`、`packages/agent/**`、`packages/core/**`、`packages/contracts/**` 或 `packages/prompts/**` 的实现 PR。

## 2. Schema 与契约边界

- [x] 2.1 定义 `IndustryEventContextV1`，覆盖 trace、source、article、industry_candidates、routing_policy 和 budget 字段，并保证 JSON-safe。
- [x] 2.2 定义 `EventIntakeDecisionV1`，覆盖 `discard` / `route` / `review`、discard reason、quality、industry relevance、structured news、routing 和 audit 字段。
- [x] 2.3 固定 schema consistency rules：discard 必须有非 `not_discarded` 原因，route 必须有目标行业，review 必须表达不确定性或人工复核需要。
- [x] 2.4 明确 `event.routed` payload 使用 `schema_version` 或等价字段标识 `event_intake_decision.v1`，避免与其他 routed payload 混淆。
- [x] 2.5 若使用 `packages/contracts/schemas/` 作为 JSON Schema 真源，补 schema 文件和重建/验证说明；若暂不用 contracts，PR 必须说明 Python 模型和 contract tests 如何先承担真源。

## 3. Context 构建与预算策略

- [x] 3.1 实现 context builder，从 `industry.analysis.requested` 中提取 message/source/binding/owner/correlation trace，不丢失 `binding_id` 和 source trace。
- [x] 3.2 实现 source/article snapshot：title、URL、RSS summary、正文或 excerpt、published time、author、language、enrichment_status、degraded_reason。
- [x] 3.3 实现 deterministic budget policy：完整正文可放入时使用完整正文，超预算时使用确定性 excerpt，仅 RSS summary 可用时标记 degraded / RSS-summary-only。
- [x] 3.4 实现 industry scope snapshot：至少支持半导体 fixture 的 direct / indirect / exclusion terms，并预留读取 enabled industry packages 的边界。
- [x] 3.5 添加测试证明 context 不包含 ORM object、plugin instance、provider client、secret-bearing runtime object、full RawEvent、full provider response 或完整 chain-of-thought。

## 4. 单次调用 Runner 与 Provider 边界

- [x] 4.1 在 `packages/agent` 或经设计说明认可的 core port 中实现 single-call intake runner；runner 只接受 bounded context 和 output schema。
- [x] 4.2 提供 `StructuredModelInvoker` 或等价受控 provider port / AgentRuntime adapter；worker 和 industry packages 不得直接创建 provider SDK client。
- [x] 4.3 添加 fake provider harness，能统计每个 article item 的 invocation 次数并返回可控 JSON 输出。
- [x] 4.4 禁止 tool-call loop、secondary fetch、multi-turn agent loop 和 chunk-by-chunk model summarization；测试中断言每个 item 最多一次 provider invocation。
- [x] 4.5 实现 schema validation failure、provider timeout/unavailable、unsupported language、malformed context 和 degraded summary-only 的结构化失败或 review 语义。

## 5. Worker Consumer 与事件路由

- [x] 5.1 在 `apps/worker` 增加或扩展 consumer composition root，订阅 `industry.analysis.requested`，但只负责 wiring / lifecycle / handler 调用。
- [x] 5.2 将 intake handler 的业务逻辑放在可测试 service/runner 边界，不把 prompt、schema、行业规则或 provider SDK 调用写进 worker entrypoint。
- [x] 5.3 实现 `event.routed` publisher，route / discard / review 三类有效 intake outcome 都必须发布，payload 必须保留 `EventIntakeDecisionV1`、trace context、decision、discard reason、target industries 和 audit summary。
- [x] 5.4 保证 `decision=discard` 不触发深度行业分析；`decision=route` 可被后续行业分析 consumer 识别；`decision=review` 保留低置信度或人工复核语义。
- [x] 5.5 更新 Event Bus contract tests 和 README，证明 `event.routed` 支持 `event_intake_decision.v1` payload 且 JSON-safe。

## 6. Fixture Harness 与验收测试

- [x] 6.1 添加 direct semiconductor fixture：HBM / DRAM / foundry / advanced packaging / chip equipment 等直接相关新闻应可 route。
- [x] 6.2 添加 indirect relevance fixture：AI server demand、hyperscaler AI capex、memory bandwidth、GPU supply chain、data center buildout 等间接相关内容不得因缺少 literal semiconductor wording 被丢弃。
- [x] 6.3 添加 unrelated / spam / SEO / low-information fixtures，断言 `decision=discard`、结构化 discard reason 和 no deep analysis。
- [x] 6.4 添加 degraded RSS-summary-only fixture，断言 context 和 decision 都保留 degraded marker，不伪装完整正文。
- [x] 6.5 添加 over-budget article fixture，断言 deterministic excerpt、content completeness metadata 和 single model invocation。
- [x] 6.6 添加 invalid model output fixture，断言 schema validation failure 不会静默 route。

## 7. 文档与 Runbook

- [x] 7.1 更新 `apps/worker/README.md`，说明 `uv run api` 不启动 AI intake consumer，consumer 需要单独由 worker/runtime 入口启动。
- [x] 7.2 更新 `packages/agent/README.md` 或新增 `event_intake/README.md`，说明 single-call runner、provider port、schema validation 和 no tool-call-loop 约束。
- [x] 7.3 如新增 prompt 资产，更新 `packages/prompts` usage note，说明 prompt 不承载 schema/policy 真源，也不保存 secret、私有策略或完整推理链。（本轮未新增 prompt 资产。）
- [ ] 7.4 在实现 PR 说明中写清未实现项：不做深度行业分析、不做 scoring/debate、不做 Decision / Approval、不做 broker。

## 8. 验证

- [x] 8.1 运行 `openspec validate ai-event-intake-single-call-routing-v1 --type change --strict --json`。
- [x] 8.2 运行受影响 Python unit tests，至少覆盖 event bus contract、worker consumer、context builder、schema validation、fake provider single-call harness。
- [x] 8.3 若新增 contracts JSON Schema，运行对应 schema validation / generation command，并确认生成物可重建。（本轮未新增 contracts JSON Schema。）
- [x] 8.4 若接入真实 provider adapter，提供 fake-provider test 为主验证；真实 provider smoke 只作为可选手工验证，不能成为 V1 acceptance 前提。（本轮未接入真实 provider adapter。）
