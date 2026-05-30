## Why

Issue #193 要把 QuantAgent 主链路从“插件能被调度调用”推进到“事件能被平台稳定发布、消费和分发”。当前 `docs/design/02-core-architecture-and-runtime.md`、`docs/design/06-source-plugin-design.md` 和 `docs/prd/03-functional-modules.md` 都把 Event Bus 放在 Source Plugin、Router Agent、Industry Plugin、Decision / Policy Gate、Persistence / Audit 和 WebSocket 之间，但仓库还没有正式 Event Bus contract。

现有设计文档仍写“初版进程内实现，后续 Redis”。维护者已决定 Event Bus V1 改为 Kafka-backed 架构，但普通本地启动和测试仍应默认使用内存 fake。本 change 先用 OpenSpec 收住架构路线、接口边界和验收口径，避免后续实现 PR 一边引入 Kafka，一边和旧设计文档的 Redis 演进路线冲突。

## What Changes

- 定义 Kafka Event Bus V1 的领域边界：`EventEnvelope`、topic policy、publisher / consumer port、handler registry、codec、内存 fake 和 Kafka adapter。
- 明确默认运行策略：测试和普通本地开发默认使用内存 fake；Kafka 通过 Compose profile 或显式环境变量启用，不作为最小启动硬依赖。
- 明确 Kafka adapter 放在 `packages/core` 内部，调用方依赖 core event bus port，不直接依赖 Kafka client。
- 明确 Event Bus V1 不做 RawEvent/Event 数据库持久化、dedupe、outbox、replay 或 DLQ 数据库记录；这些只预留接口边界并拆后续 issue。
- 明确插件隔离：Plugin SDK / RuntimeContext 不暴露 Event Bus publisher；只能由平台 service 在插件调用成功后把 typed output 转换并发布事件。
- 明确 worker / scheduler 后续只是 composition root，负责启动 publisher / consumer，不承载事件协议；API 不启动长期 consumer loop。
- 记录与旧设计冲突的回写点：`docs/design/01-tech-stack-and-project-structure.md`、`docs/design/02-core-architecture-and-runtime.md`、`docs/design/10-deployment-and-runtime-design.md` 后续需要从“内存 / Redis 演进”调整到“内存 fake 默认 + Kafka 可选运行时”。

## Capabilities

### New Capabilities

- `kafka-event-bus-v1`: 定义 QuantAgent Event Bus V1 的 envelope、topic、port、内存 fake、Kafka adapter、运行配置、插件隔离和验证 contract。

### Modified Capabilities

- 无。当前仓库没有已归档 Event Bus stable spec；本 change 只新增 `kafka-event-bus-v1` capability，并在后续 PR 中回写设计文档。

## Impact

- 后续实现主要影响 `packages/core/src/quantagent/core/events/` 或等价 event bus 目录，以及 `packages/core/tests/**`。
- 后续实现会影响根目录 Docker Compose、`.env.example` 和 core 配置读取，但 Kafka 应保持显式启用。
- 后续 worker / scheduler 会通过 core port 接入 Event Bus；`apps/api` 不承载长期 consumer loop。
- 后续设计文档需要回写 Event Bus 技术路线，说明为什么从 Redis 演进改为 Kafka。
- 不影响 `apps/web`，不新增 REST / WebSocket API，不新增数据库迁移，不引入真实交易或生产 broker 能力。
