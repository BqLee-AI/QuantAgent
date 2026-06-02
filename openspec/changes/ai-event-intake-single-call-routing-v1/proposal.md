## 为什么

#266 要承接 `industry.analysis.requested` 之后的下一跳：用受控 AI consumer 判断一篇文章是否值得进入更贵的行业深度分析。若没有正式契约，路由阶段容易漂移成多次模型调用、工具循环、worker / agent / 行业包各自定义 schema，以及丢弃结果不可审计。

本 change 固定 V1 边界：每篇文章 intake 最多一次结构化模型调用；这一次调用必须同时完成过滤、结构化、行业相关性判断和路由。

## 变化内容

- 新增 V1 AI event intake 能力：消费 `industry.analysis.requested`，产出 schema 校验后的 `EventIntakeDecisionV1`。
- 定义紧凑的 `IndustryEventContextV1` 输入规则：source trace、enrichment / degraded 状态、受限正文、启用行业包 scope snapshot、routing policy 和预算元数据。
- 定义 single-call 约束：不允许模型工具调用、多轮 Agent loop、二次抓取网页，也不允许在 V1 intake 内用模型分块总结后再路由。
- 定义 `discard` / `route` / `review` 三类结果语义，并覆盖 spam、irrelevant、duplicate hint、low-information、unsupported language、malformed 等结构化 discard reason。
- 定义路由结果 handoff 进入稳定 Event Bus 契约：使用 `event.routed` 承载 schema-safe triage / routing 输出，不新增未评审的临时 topic。
- 定义审计和安全边界：event payload 不包含 ORM object、plugin instance、secret、完整 provider raw response 或完整 chain-of-thought。
- 定义 fixture-based 验证：覆盖半导体直接相关、AI 基建间接相关、无关内容、spam / SEO 噪音、degraded RSS-only 输入、超预算正文和非法模型输出。

## 能力变化

### 新增能力

- `ai-event-intake-routing`: 定义从 `industry.analysis.requested` 开始的 single-call AI intake、紧凑 context 构建、结构化 intake decision、discard / route / review 语义、校验、审计和下游路由 handoff。

### 修改能力

- `kafka-event-bus-v1`: 将 `event.routed` 明确作为 V1 AI intake routing decision 的正式输出 topic，并要求 payload 保留 trace context 和 JSON-safe 结构化路由数据。

## 影响范围

- `apps/worker/**`: 后续实现新增或扩展 `industry.analysis.requested` consumer composition root，但 worker 入口仍保持薄层。
- `packages/agent/**`: 后续实现 single-call intake runner / provider port，或在 AgentRuntime 可用时复用 AgentRuntime。
- `packages/core/**`: 后续实现 Event Bus contract 更新、跨 worker/agent 复用的 context/result model、结果校验和 audit-safe routing helper。
- `packages/contracts/**`: 后续实现可新增 `IndustryEventContextV1` 和 `EventIntakeDecisionV1` JSON Schema；只有实现 PR 明确生成路径时才提交生成产物。
- `packages/prompts/**`: 后续实现可新增 bounded prompt template，但 schema 和 policy 不能只藏在 prompt 文本里。
- Event Bus contract：`event.routed` 成为 V1 AI intake routing 的稳定输出；不应引入未经过 OpenSpec 的新 topic 字符串。
- Runtime / provider governance：模型调用必须经过 AgentRuntime / provider policy，或经过为 V1 fake-provider harness 设计的受控 provider port；worker 和行业包不得直接实例化 provider SDK client。
