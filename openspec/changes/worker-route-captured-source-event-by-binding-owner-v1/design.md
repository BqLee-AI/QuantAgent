## Context

issue #224 要收住的是 worker 从“能收到 `source.event.captured`”推进到“能按 binding/owner 把事件送入正确行业处理入口”的边界。当前已有真源提供了部分前提：

- `openspec/changes/scheduling-event-bus-bridge-v1/**` 已定义 scheduler / plugin scheduling 在 `source.fetch` 成功后发布 `source.event.captured`。
- `openspec/changes/source-binding-scheduler-run-persistence-v1/**` 与当前 `packages/core/src/quantagent/core/scheduling/**` 已定义 `SourceBinding` / `SchedulerRun` 的持久化主对象、service seam 和 `binding_id` / `run_id` 关联位点。
- `docs/design/06-source-plugin-design.md` 明确调度主对象是 `SourceBinding`，同一 source plugin 可以被多个 owner 复用，因此不得按裸 `source_plugin_id` 路由。
- `docs/design/07-industry-package-design.md` 明确行业包是 `owner_type=industry` 的首个主消费者，但行业包不能被 worker 直接硬编码 import。
- `apps/worker` 当前只有 composition root 和最小测试，不存在真实 consumer / handler / routing service。

本 change 是行为与分层边界 change，不实现代码；但它必须把未来实现的目录、文件职责、事件字段、service 边界、失败路径和验证入口写具体，否则实现阶段仍会临场拍脑袋。

## Goals / Non-Goals

**Goals:**

- 定义 worker 路由的目录蓝图和职责分层，让 `apps/worker` 保持薄入口，把可复用路由能力下沉到 `packages/core`。
- 定义 `source.event.captured` 供 worker 路由使用的最小字段，至少稳定包含 `binding_id`，并继续保留 `request_id` / `plugin_id` / item 信息。
- 定义 `SourceBinding` -> owner -> 行业入口解析链路，明确 V1 只成功支持 `industry` owner，其余 owner 返回受控失败。
- 定义重复消息、binding 缺失、binding 非 active、owner 不支持、行业入口失败的处理语义。
- 定义与 #217、#221 的协作边界，避免本轮扩大到 scheduler loop 或 RawEvent 持久化。

**Non-Goals:**

- 不实现完整行业分析、Router Agent、Decision、Approval、Notification 或 broker 执行链路。
- 不把 worker 入口变成行业插件硬编码注册表，不在 app 层直接 import 具体行业实现列表。
- 不定义多 owner 的完整行为矩阵；V1 只要求 `industry` 成功路径，其他 owner 先保持兼容失败。
- 不实现 RawEvent 入库、事件去重数据库、DLQ 持久化或通用 replay 基础设施。
- 不引入新的 app/package；仍沿用 `apps/worker` 与 `packages/core` 边界。

## Decisions

### 1. 采用四段式链路：consumer handler -> routing service -> owner resolver -> industry entrypoint gateway

目录蓝图：

```text
apps/worker/src/quantagent/worker/
  main.py                         # composition root，只组装 runtime / consumer / handler
  consumer/
    captured_event_handler.py     # 只负责订阅 topic、解码 envelope、调用 routing service
  README.md                       # 记录 worker 入口职责与不要放什么

packages/core/src/quantagent/core/
  worker_routing/
    __init__.py
    models.py                     # 路由输入/输出与失败结果 DTO
    captured_event_decoder.py     # 从 EventEnvelope 提取 binding_id / request_id / plugin_id
    service.py                    # WorkerCapturedEventRoutingService，编排 binding 查询与 owner 解析
    owner_resolver.py             # 解析 owner_type / owner_id 到受控入口引用
    industry_gateway.py           # 行业入口调用 seam，不直接依赖具体插件实现
    README.md                     # 中文说明职责、边界、入口与非目标

packages/core/tests/
  test_worker_captured_event_routing.py
```

职责：

- `captured_event_handler.py` 只做消费编排和 lifecycle，不持有业务规则。
- `captured_event_decoder.py` 只做 envelope -> routing input 映射和字段校验。
- `service.py` 负责查询 binding、过滤状态、检测重复、调用 resolver/gateway，并产出结构化结果。
- `owner_resolver.py` 只把 `owner_type + owner_id` 转成受控入口引用，不直接 import 具体行业实现。
- `industry_gateway.py` 是 worker 与后续行业处理服务之间的 core port；V1 可以先用 fake / no-op 实现占位，但无论是否真正触发行业处理，都必须返回结构化 `IndustryGatewayResult`，且禁止直接 import 行业插件或在 gateway 内硬编码插件注册分支。

选择这套分层而不是在 `apps/worker/main.py` 里直接写 if/else，原因：

- 符合 `apps/worker` 薄入口与 `packages/core` 共享 seam 约束。
- 后续 #217 可能需要在 scheduler / replay / backfill 场景复用同一套路由服务，不应锁死在 worker app 内。
- owner 解析与行业入口调用都是稳定边界，值得独立成 service / resolver / gateway，而不是散落在 handler。

备选方案：

- 直接在 worker handler 中按 `owner_type` 写大 if/else 并 import 行业实现。放弃原因是会违反 plugin/registry 边界，且很快变成不可测试的大文件。

### 2. `source.event.captured` 必须补齐稳定 `binding_id`，worker 禁止按 `plugin_id` 粗路由

V1 worker 路由输入必须至少包含：

```text
message_id
topic
binding_id
request_id
plugin_id
item_count
correlation_id
causation_id
payload.items
payload.metadata
```

约束：

- `binding_id` 是 worker 路由的一级真源；缺失时必须返回结构化失败，不能回退为按 `plugin_id`、`owner_id` 猜测路由。
- `request_id` / `correlation_id` 继续作为审计与幂等辅助字段。
- `plugin_id` 只作为诊断字段，不作为目标 owner 的选择依据。

原因：

- 同一 source plugin 可被多个 owner 复用；按 `plugin_id` 路由必然失真。
- #216 / #226 已经把 `binding_id` 固定为调度与 API 侧的一级关联位点；worker 必须复用同一命名。

备选方案：

- 依赖 `request_id` 查 `SchedulerRun` 再反推 binding。放弃原因是额外耦合 `SchedulerRun` 查询链路，而且 `request_id` 更适合作为审计关联，不应替代 binding 主对象。

### 3. V1 成功路径只支持 `owner_type == "industry"`，其他 owner 受控失败

`owner_resolver` 规则：

```text
if owner_type == "industry":
  -> 返回 IndustryEntrypointRef(owner_id=..., binding_id=...)
else:
  -> 返回 UnsupportedOwnerRoutingFailure(owner_type=...)
```

原因：

- `docs/design/07-industry-package-design.md` 已明确行业包是首个通过 `SourceBinding` 消费 source 事件的 owner。
- issue #224 用户约束明确要求不要扩到 #217 / #221 之外，更不能把 future runtime/private owner 行为在本轮提前实现。
- 先把扩展位保留在 resolver seam，而不是在 V1 同时做多 owner 分支。

备选方案：

- 立刻做 multi-owner registry。放弃原因是没有现成真源支撑，容易越过 issue 范围。

### 4. `industry_gateway` 在 V1 收敛为 core port，允许 fake / no-op，但结果必须结构化

`industry_gateway.py` 在 V1 的定位不是“直接跑行业插件”，而是 `packages/core` 暴露给 worker routing service 的受控 port。它的职责只有两类：

- 接收已完成 owner 解析的 `IndustryEntrypointRef` 和 captured event 路由输入；
- 返回结构化 `IndustryGatewayResult`，让 routing service 能统一产出 `WorkerRouteResult`，而不是靠异常字符串或插件私有返回值猜测结果。

V1 约束：

- gateway 所在位置必须是 `packages/core/src/quantagent/core/worker_routing/industry_gateway.py` 或等价 core seam，不能下沉到具体行业插件目录。
- gateway 可以先接 future service seam、fake adapter 或 no-op adapter，但返回值必须稳定包含 `status`、`reason_code`、`target_ref`、`attempted_at`、`error_summary`（失败时）等结构化字段。
- gateway 不得直接 import `plugins/industries/*`、行业包 Python 模块、插件 class，或写死 `if industry == "oil"` 之类注册逻辑。
- worker handler 和 routing service 只能依赖 gateway port / protocol，不依赖任何具体行业实现细节。

原因：

- 这条 seam 是后续接 AgentRuntime / ToolRegistry / industry package 的唯一安全入口，必须先把依赖方向固定在 core port。
- V1 没有要求真实行业链路已落地，因此 fake / no-op 是允许的；但如果返回值不结构化，实现 PR 就会重新滑回“看日志或吞异常”的状态。

### 5. 重复消息检测使用“消息级幂等键 + 结构化结果”，但不在本轮定义持久化去重基础设施

V1 结果模型建议：

```text
WorkerRouteResult
  message_id
  binding_id
  status                # routed / ignored / failed / duplicate
  owner_type
  owner_id
  route_target
  reason_code
  audit_payload
```

处理规则：

- 相同 `message_id` 或等价幂等键重复进入时，routing service 必须返回 `duplicate`，并保持“可安全重试但不重复下游副作用”的语义。
- 本轮不强制定义持久化幂等表；可以先由 future runtime seam 或 consumer backend 提供幂等 guard，但 spec 必须把语义写死。
- 之所以现在只写语义不写持久化实现，是因为 #221 将为 RawEvent / replay / dedupe 提供更稳定的持久化真源。

备选方案：

- 完全依赖 Kafka consumer group 保障不重复。放弃原因是这只能减少重复消费，不能替代业务幂等语义。

### 6. 失败路径采用“结构化失败 + 可审计结果”，不把异常静默吞掉

V1 路由结果矩阵至少覆盖以下 reason code：

- `CAPTURED_EVENT_BINDING_ID_MISSING`
- `SOURCE_BINDING_NOT_FOUND`
- `SOURCE_BINDING_NOT_ACTIVE`
- `CAPTURED_EVENT_OWNER_UNSUPPORTED`
- `CAPTURED_EVENT_DUPLICATE`
- `INDUSTRY_ENTRYPOINT_FAILED`

| reason_code | route_status | consumer_disposition | retryable | audit_required |
| --- | --- | --- | --- | --- |
| `CAPTURED_EVENT_BINDING_ID_MISSING` | `failed` | `ack_and_record_failure` | `false` | `true` |
| `SOURCE_BINDING_NOT_FOUND` | `failed` | `ack_and_record_failure` | `false` | `true` |
| `SOURCE_BINDING_NOT_ACTIVE` | `ignored` | `ack_and_record_ignored` | `false` | `true` |
| `CAPTURED_EVENT_OWNER_UNSUPPORTED` | `failed` | `ack_and_record_failure` | `false` | `true` |
| `CAPTURED_EVENT_DUPLICATE` | `duplicate` | `ack_and_record_duplicate` | `false` | `true` |
| `INDUSTRY_ENTRYPOINT_FAILED` | `failed` | `nack_or_schedule_retry` | `true` | `true` |

语义：

- `consumer_disposition` 是 worker consumer 对本条消息的处理决定真源，必须和 `WorkerRouteResult` 一起可审计，不能只藏在 transport 实现里。
- `CAPTURED_EVENT_BINDING_ID_MISSING`、`SOURCE_BINDING_NOT_FOUND`、`CAPTURED_EVENT_OWNER_UNSUPPORTED` 都属于契约或配置问题；V1 统一 `ack_and_record_failure`，避免无意义重试。
- `SOURCE_BINDING_NOT_ACTIVE` 明确收敛为 `ignored`，因为该 binding 已存在但当前不允许投递；worker 应确认消费并记录忽略原因，而不是把它当作瞬时故障反复重试。
- `CAPTURED_EVENT_DUPLICATE` 必须确认消费并记录 duplicate 审计，不得再次触发下游副作用。
- `INDUSTRY_ENTRYPOINT_FAILED` 是唯一在 V1 映射中默认 `retryable=true` 的场景；consumer 可以选择 `nack` 或调度受控重试，但无论采用哪种 transport 细节，都必须保留结构化失败结果。

原因：

- 仓库规则要求关键状态变化与高风险动作可审计。
- 若继续只靠日志字符串，后续 #217 的 replay 与 #221 的归属链路都无法稳定复用。

### 7. 与 #217 / #221 的边界以“输入位点”和“输出位点”协作，不交叉实现

与 #217 的协作：

- #217 负责确保 scheduler 以 `SourceBinding` 为主对象运行，并在发布 captured 事件时复用 `binding_id`。
- #224 不负责 scheduler interval loop、next run 计算或 run history 回写。

与 #221 的协作：

- #221 负责 RawEvent 持久化、去重和 `binding_id` / `run_id` 归属真源。
- #224 不负责 RawEvent 入库或 dedupe 表，只要求 worker routing 语义可以复用同一归属字段和重复处理口径。

原因：

- 三个 issue 都围绕 `binding_id`，但职责不同：#217 负责生产 captured 事件，#224 负责消费并路由，#221 负责原始事件落库与去重真源。

## Risks / Trade-offs

- [Risk] 当前 `scheduling-event-bus-bridge-v1` 实现尚未携带 `binding_id`。  
  Mitigation：本 change 显式把 `binding_id` 升级为 captured 事件契约要求，并把实现依赖写进 tasks。

- [Risk] V1 只支持 `industry` owner，可能让后续扩展 owner 类型再改 resolver。  
  Mitigation：把 owner 解析放进独立 seam，未来新增 owner 只扩展 resolver，不改 handler。

- [Risk] 没有持久化幂等表时，重复消息只能先有语义约束，不能完全证明跨进程幂等。  
  Mitigation：本轮把 duplicate 结果语义写死，持久化去重基础设施留给后续 RawEvent / replay change。

- [Risk] 如果直接让 worker gateway 调具体行业插件，会把核心运行时边界绕穿。  
  Mitigation：spec 明确 gateway 是受控 port，不得硬编码 import 行业实现列表。

## Migration Plan

1. 提交本 OpenSpec-only PR，只包含 `worker-route-captured-source-event-by-binding-owner-v1/**`。
2. 维护者明确评论“没问题”或批准后，再进入实现 PR。
3. 实现 PR 先修改 captured 事件发布契约，确保 `binding_id` 可用。
4. 再在 `packages/core` 增加 worker routing seam，并在 `apps/worker` 只组装 consumer handler。
5. 最后补最小单元测试，验证成功路由、缺 binding、非 active、owner 不支持、duplicate、下游失败六类场景。

回滚策略：

- OpenSpec-only PR 无运行时变更，可直接关闭或重提。
- 后续实现 PR 如果已修改事件契约，回滚必须通过新的 forward-fix 保持 `binding_id` 字段一致，不允许局部回退成按 `plugin_id` 路由。

## Open Questions

- `binding_id` 放在 captured 事件 `payload`、`headers`，还是两者都保留；默认建议至少在一个稳定字段中强制存在，并避免只有 header 可见。
