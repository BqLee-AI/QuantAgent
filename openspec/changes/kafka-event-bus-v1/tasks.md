## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `openspec/changes/kafka-event-bus-v1/**` 和必要说明，不混入实现、依赖升级、格式化或设计文档回写。
- [x] 1.2 在 PR 说明中链接 issue #193，并写清楚：本 change 把旧的“进程内 / Redis 演进”调整为“内存 fake 默认 + Kafka 可选运行时”。
- [x] 1.3 运行 `openspec validate kafka-event-bus-v1 --type change --strict --json`。
- [x] 1.4 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. Core Event Bus Contract

- [x] 2.1 在 `packages/core` 事件目录中实现 `EventEnvelope`，字段包含 `id`、`topic`、`payload`、`producer`、`created_at`、`correlation_id`、`causation_id`、`headers`、`retry_count`、`schema_version`。
- [x] 2.2 实现 JSON-safe 校验，禁止 envelope 携带 DB session、ORM model、插件实例、scheduler、内部 service、secret resolver 或不可序列化对象。
- [x] 2.3 实现 V1 topic policy，默认允许 spec 中列出的 13 个 topic，未知 topic 以结构化错误拒绝。
- [x] 2.4 实现 `EventBusPublisher`、`EventBusConsumer`、`EventBusHandler`、`EventBusCodec`、`EventTopicPolicy` 等 core port，不让调用方直接依赖 Kafka client。
- [x] 2.5 为 event bus 目录补 README / usage note，说明职责、调用入口、不要放什么，以及插件不能直接发布事件的原因。

## 3. Memory Backend

- [x] 3.1 实现内存 fake backend，作为测试和普通本地开发默认 backend。
- [x] 3.2 内存 fake 必须复用 envelope 校验、topic policy、codec 和 handler contract。
- [x] 3.3 验证无 Kafka 配置时 core 单元测试可以发布、订阅和 dispatch handler。
- [x] 3.4 验证 handler 异常不会被吞掉，并能形成可断言的结构化失败。

## 4. Kafka Backend

- [x] 4.1 实现前确认 Python Kafka 客户端选型：检查 lockfile、已安装版本、维护状态和官方文档，并在 PR 说明取舍。
- [x] 4.2 将 Kafka adapter 放在 `packages/core` event bus 边界内，并保持 Kafka client 为实现细节。
- [x] 4.3 实现 Kafka producer publish、consumer subscribe、consumer group、成功 handler 后 ack / commit、graceful shutdown 和 readiness / health helper。
- [x] 4.4 支持 `EVENT_BUS_BACKEND=memory|kafka` 或等价 settings，并为 Kafka bootstrap servers、client id、default group id、topic prefix 提供环境变量覆盖入口。
- [x] 4.5 更新 Docker Compose / `.env.example` 时保持 Kafka 显式启用，不作为普通本地启动硬依赖。

## 5. Platform Integration Boundaries

- [x] 5.1 保持 Plugin RuntimeContext 禁止暴露 `event_bus`、publisher、consumer、DB session、ORM model、scheduler、internal service 或 secret resolver。
- [x] 5.2 为 Plugin Scheduling / future SourceIngestionService 预留“typed output -> platform normalization -> EventEnvelope -> EventBusPublisher.publish”的平台 service 边界。
- [x] 5.3 worker / scheduler 只能作为 composition root 启动 core publisher / consumer，不定义 envelope 字段、topic policy 或 Kafka serialization。
- [x] 5.4 API 只能作为管理、健康检查或薄触发边界，不在 request handler 中启动长期 consumer loop。

## 6. Validation

- [x] 6.1 添加 contract tests 覆盖 envelope 必填字段、schema_version、correlation / causation、JSON-safe payload / headers 和敏感信息脱敏。
- [x] 6.2 添加 topic policy tests 覆盖默认 topic 集合和未知 topic 拒绝。
- [x] 6.3 添加 memory backend tests 覆盖 publish、subscribe、handler dispatch、handler failure 和无 Kafka 本地运行。
- [x] 6.4 添加 Kafka adapter 显式开关 integration test 或 smoke harness；未启动 Kafka 时测试必须可跳过且原因清晰。
- [x] 6.5 添加配置解析验证，证明 memory 默认可用，Kafka backend 缺少 bootstrap servers 时返回结构化配置错误。
- [x] 6.6 验证日志、error summary、headers 和 payload diagnostics 不暴露 secret、token、cookie、完整本地私有路径、完整 prompt 或私有策略。

## 7. Design 回写与后续拆分

- [x] 7.1 实现 PR 或单独文档 PR 回写 `docs/design/01-tech-stack-and-project-structure.md` 的 Event Bus 技术栈表。
- [x] 7.2 回写 `docs/design/02-core-architecture-and-runtime.md` 的 EventEnvelope / Topic / Kafka 运行语义。
- [x] 7.3 回写 `docs/design/10-deployment-and-runtime-design.md`，将 Redis 演进章节调整为 Kafka 可选运行时和内存 fake 默认策略。
- [x] 7.4 如果实现中需要 RawEvent 持久化、dedupe、outbox、replay 或 DLQ 数据库记录，停止扩大范围并另开 issue / OpenSpec。
