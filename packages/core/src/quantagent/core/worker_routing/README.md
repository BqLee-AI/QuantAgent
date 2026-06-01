# worker_routing

该目录承接 worker 消费 `source.event.captured` 后的路由真源，不承接具体行业分析实现。

职责：

- `captured_event_decoder.py` 只做 `EventEnvelope -> CapturedSourceEventInput` 的字段提取与最小校验。
- `service.py` 负责 `binding_id` 查询、duplicate 语义、owner 解析、gateway 调用与结构化结果映射。
- `owner_resolver.py` 只负责把 `SourceBinding.owner_type / owner_id` 解析为受控入口引用。
- `industry_gateway.py` 是行业入口的 core port；V1 允许 no-op/fake，但必须返回结构化结果。
- `models.py` 固定 route status、consumer disposition、audit payload 等 worker 契约。

不要放什么：

- 不直接 import `plugins/industries/*` 或具体行业插件类。
- 不在这里实现 RawEvent 落库、通用 replay 基础设施或完整行业分析链路。
- 不把 Kafka/transport 细节和业务路由规则混在同一个 handler。
