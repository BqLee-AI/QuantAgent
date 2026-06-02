## Why

QuantAgent 当前已经分别推进了 RSS source 插件、Readability source 插件、`SourceBinding Template / Effective Config` 契约、`SourceBinding / SchedulerRun` 持久化、scheduler 事件桥接，以及 worker 按 `binding_id -> owner` 路由的边界。但这些能力仍停留在“基础件已就位、产品级主链路未收口”的状态，仓库里还没有一份 OpenSpec 明确回答：

- 半导体 / 内存行业包如何把 RSS 作为 required source、把 Readability 作为 optional enrichment source 接入。
- `RSS -> Readability` 的正文增强应放在哪个平台边界，而不是被塞进 RSS 插件、scheduler 或行业包内部。
- `source.event.captured` 之后，半导体行业链路究竟是直接 service handoff，还是发布 `industry.analysis.requested` 进入后续 AI / AgentRuntime 消费。
- 正文增强失败时是中断主链路还是显式降级消费 RSS 摘要。
- RSS capture 事实与 enrichment 后分析输入之间的先后关系如何保持稳定真源。

如果没有这张 change，后续半导体行业包实现、worker/AgentRuntime 接线、Event Bus topic 变更、RawEvent 接入和模板资产都会各自补一部分判断，最后出现 topic 漂移、插件边界回退和 PR 范围失控。

## What Changes

- 新增一个半导体 / 内存行业包首条 source ingestion 主链路的 OpenSpec capability。
- 固定行业包依赖关系：RSS 作为 required discovery source，Readability 作为 optional article enrichment source。
- 固定 `RSS -> Readability` 编排点：worker 在消费 `source.event.captured` 之后通过受控 enrichment seam 决定是否抓正文。
- 固定分析入口：worker 在 owner 路由与 enrichment 之后发布 `industry.analysis.requested`，而不是直接把半导体分析实现硬编码进 worker。
- 固定降级策略：Readability 失败不阻断主链路，但必须显式标记 degraded / enrichment_failed 状态。
- 固定 RSS capture 与后续分析输入的关系：RSS capture 先进入平台事实层，enrichment 影响后续分析输入，不成为 capture 真源存在的前提。

## Capabilities

### New Capabilities

- `semiconductor-source-ingestion`: 定义半导体 / 内存行业包默认 RSS + Readability ingestion 主链路的 source dependency、worker enrichment、analysis-request topic handoff 和降级语义。

### Modified Capabilities

- `worker-captured-source-routing`: 从“按 binding owner 路由到行业入口”扩展为“对半导体 owner 的 captured source item 完成 enrichment 编排后发布 `industry.analysis.requested`”。
- `scheduling-event-bus-bridge-v1`: 继续作为 `source.event.captured` 的上游桥接契约真源，但本 change 不修改其“先发布 capture、后做 enrichment”的职责边界。
- Event Bus stable topic contract：`industry.analysis.requested` 在本主链路中成为明确采用的 handoff topic，需要同步 topic policy 和 contract tests。

## Impact

- `plugins/industries/` 后续需要新增官方半导体 / 内存行业包样例或正式包，声明 RSS required + Readability optional 的 `source_bindings`。
- `packages/core/src/quantagent/core/worker_routing/**` 后续需要新增 enrichment seam、degraded metadata 语义，以及 analysis-request publisher 行为。
- `packages/core/src/quantagent/core/events/**` 后续需要把 `industry.analysis.requested` 作为主链路使用的稳定 topic 契约继续验证。
- `packages/core/src/quantagent/core/raw_events/**` 与 scheduler/source ingestion 相关实现后续需要复用“RSS capture 先入事实层”的顺序，不允许让 Readability 成为 capture 存在的前置条件。
- 本 PR 只新增 `openspec/changes/semiconductor-rss-readability-ingestion-main-chain-v1/**`，不混入实现代码、测试代码、依赖升级或格式化。
