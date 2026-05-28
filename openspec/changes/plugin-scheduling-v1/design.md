## 背景

Plugin Scheduling V1 位于 Registry、Runtime 和 Plugin IO DTO 之后。Registry 负责发现和校验插件，Runtime 负责单次加载、生命周期和 invoke，IO DTO 负责 capability 的 typed input/output；Scheduling V1 负责把“何时调用、用什么配置调用、如何记录 run 状态”收成平台能力。

本设计以 issue #141、`docs/design/02-core-architecture-and-runtime.md`、`docs/design/03-plugin-system-and-registry.md`、`docs/design/06-source-plugin-design.md` 和已合入的 `plugin-runtime-v1` / `plugin-io-dto-v1` 为真源。

## 目标与非目标

目标：

- 支持手动 trigger 某个已注册插件 capability。
- 支持最小 interval 调度 contract，后续可由 worker/scheduler loop 执行。
- 记录每次 run 的状态、时间、duration、错误摘要和最小 metadata。
- 对 Runtime invoke 增加调度层 timeout、异常归类和结构化错误保存。
- 保持插件不自调度，避免 while loop、后台线程、私有 ticker。

非目标：

- 不实现 RawEvent 入库、Event Bus 发布、SourceBinding 全量模型或复杂 retry。
- 不把调度循环塞进 FastAPI router。
- 不改变 Runtime V1 transport 或 Plugin IO DTO 字段。
- 不要求本轮实现真实后台 worker；OpenSpec 只定义实现蓝图和验收边界。

## 分层与目录蓝图

后续实现建议采用以下边界：

```text
packages/core/src/quantagent/core/scheduling/
  __init__.py
  models.py
  service.py
  repository.py
  clock.py

packages/core/tests/test_scheduling.py
```

职责：

- `models.py`：定义 scheduling 领域 DTO / domain model，例如 `PluginRunStatus`、`PluginTriggerType`、`PluginRunRecord`、`PluginTriggerRequest`、`IntervalSchedulePolicy`。
- `service.py`：编排 Registry record、Runtime invoke、timeout、run 状态迁移和错误归档。
- `repository.py`：定义 run repository / storage port，V1 可先提供内存实现用于测试；后续数据库实现不改变 service contract。
- `clock.py`：提供可注入 clock，测试 duration、timeout 和下一次 interval 计算时避免依赖真实时间。
- `tests/test_scheduling.py`：覆盖手动 trigger、成功 run、失败 run、timeout run、interval next_run 计算和插件禁止自调度边界。

如果后续需要 API：

```text
apps/api/.../plugins_or_scheduling_routes.py
```

API 只负责 HTTP 参数、认证、响应 envelope 和调用 core scheduling service，不承载 run 状态机或长期循环。

## 核心模型草案

```text
PluginTriggerRequest
  plugin_id: string
  capability: string
  request_id: string
  trigger_type: "manual" | "interval"
  input: object
  effective_config: object
  metadata: object
  timeout_ms: integer | null

PluginRunRecord
  run_id: string
  plugin_id: string
  plugin_version: string | null
  capability: string
  request_id: string
  trigger_type: "manual" | "interval"
  status: "queued" | "running" | "succeeded" | "failed" | "timeout" | "cancelled"
  started_at: string | null
  finished_at: string | null
  duration_ms: integer | null
  timeout_ms: integer | null
  output_summary: object
  error_summary: object | null
  metadata: object

IntervalSchedulePolicy
  interval_seconds: integer
  jitter_seconds: integer | null
  enabled: boolean
  metadata: object
```

字段约束：

- `input`、`effective_config`、`metadata`、`output_summary` 和 `error_summary` 必须是 JSON-like object，并只包含 JSON-safe values。
- `request_id` 必须由调用方或 Scheduling 在 run 创建前生成；`PluginRunRecord.request_id` 不允许为空。
- `effective_config` 表示平台校验后的配置，不允许插件自行读取 DB 或未治理的本地配置。
- `output_summary` 只保存可审计摘要，不在本轮承诺 RawEvent 入库或完整原始 payload 持久化。
- `error_summary` 不得泄露 secret、token、cookie、完整本地路径或原始 stack trace。

## 状态机

```text
queued
  -> running
  -> succeeded
  -> failed
  -> timeout
  -> cancelled
```

约束：

- 每次 run 必须有唯一 `run_id` 和 `request_id`。
- `running` 必须记录 `started_at`。
- 终态必须记录 `finished_at` 和 `duration_ms`。
- `succeeded` 表示 Runtime invoke 成功返回 `PluginInvokeResult`，但不代表后续入库或 Event Bus 成功。
- `failed` 表示 Registry 记录不可加载、Runtime load/start/invoke/stop 失败、DTO 校验失败或插件结构化错误。
- `timeout` 表示调度层等待 Runtime invoke 超过 `timeout_ms`；timeout 需要保存结构化错误摘要。
- `cancelled` 预留给后续人工取消或 worker shutdown，V1 可只定义状态不实现外部取消 API。

## 数据流

### 手动 trigger

```text
API / test harness / worker
  -> PluginSchedulingService.trigger(request)
  -> PluginRegistry 查找有效 PluginRecord
  -> 创建 queued run
  -> 标记 running
  -> PluginRuntimeService.invoke(record, capability=capability, request_id=request_id, config=effective_config, input=input, metadata=metadata)
  -> 根据 invocation result 写 succeeded / failed / timeout
  -> 返回 PluginRunRecord
```

### interval 调度

```text
Interval policy / future binding
  -> scheduler loop 计算 due run
  -> 构造 PluginTriggerRequest(trigger_type="interval")
  -> 调用同一个 PluginSchedulingService.trigger
  -> 保存 run 状态
```

V1 只要求 interval 调度复用同一个 trigger service，不要求本轮实现长期 scheduler loop。

## 失败路径

- Registry 找不到插件或插件不是 valid：run 进入 `failed`，stage 归因到 `load` 或 `schedule_precheck`。
- capability 未声明：run 进入 `failed`，错误 code 对齐 Runtime V1 的 `PLUGIN_CAPABILITY_UNAVAILABLE`。
- config 缺失或 effective_config 非 JSON-safe：run 进入 `failed`，stage 可归因到 `config`。
- input 非 JSON-safe 或 DTO 校验失败：run 进入 `failed`，stage 可归因到 `invoke`。
- Runtime invoke 抛异常或返回结构化 error：run 进入 `failed`，保存脱敏 error summary。
- timeout：run 进入 `timeout`，保存 `timeout_ms`、stage 和 timeout error_summary。
- 成功但空结果：run 进入 `succeeded`，output_summary 可以表达空结果，不等同失败。

## 复用与不复用

复用：

- 复用 `PluginRecord` / `PluginManifest` / `PluginError`。
- 复用 `PluginRuntimeService.invoke`，不重新实现插件加载和生命周期。
- 复用 `PluginInvokeRequest` / `PluginInvokeResult` transport 和 Plugin IO DTO 的 JSON-safe 约束。

不复用 / 不提前抽象：

- 不把 scheduling 逻辑塞进 `PluginRuntimeService`，避免 Runtime 变成 scheduler。
- 不在 `BasePlugin` 增加 scheduling hook，插件不应感知调度循环。
- 不提前引入队列、cron parser、distributed lock 或数据库 migration，除非实现 PR 明确需要。

## 验证策略

OpenSpec-only PR：

- 运行 `openspec validate plugin-scheduling-v1 --type change --strict --json`。

后续实现 PR 最小验证：

- 手动 trigger 成功 run：状态从 running 到 succeeded，保存 duration_ms 和 output_summary。
- Runtime 结构化失败 run：状态 failed，保存脱敏 error_summary。
- timeout run：状态 timeout，保存 timeout_ms、finished_at 和 duration_ms。
- 空结果 run：状态 succeeded 且 output_summary 表达空集合。
- interval policy：计算下一次 due run 或构造 interval trigger request。
- 插件不自调度：测试或 review 确认实现不向 plugin SDK 暴露 scheduler / DB / Event Bus。
