## 为什么现在做

Issue #141 要解决的是插件底座从“能被 Runtime 调用”推进到“由平台触发并记录运行状态”。当前 Registry 已能发现插件，Runtime V1 已能加载并 invoke 插件，Plugin IO DTO V1 已开始收住 capability-specific 输入输出；但平台还缺一层调度/触发边界来决定什么时候调用插件、如何注入 effective config、如何记录每次 run 的状态和错误。

如果没有 Plugin Scheduling V1，pull source 插件容易退回自己写 `while` loop、后台线程或私有定时器；API router 也可能被误用成长任务执行器。这样会破坏插件生命周期、配置治理、审计和后续 worker/scheduler 演进边界。

## 当前缺口

- Runtime V1 只负责单次加载、生命周期和统一 invoke，不负责手动 trigger、interval 调度或 run 状态记录。
- Source design 已明确 pull source 必须由统一 Scheduler 管理，但 SourceBinding / Scheduler 的完整实现还不是本轮范围。
- 系统缺少 `PluginRun` / `PluginTriggerRequest` 级别的最小状态和错误语义，后续 source、notification、worker 和 API 很难用同一套 harness 验证。

## 本轮目标

- 定义平台手动 trigger 插件 capability 的最小 contract。
- 定义第一版 interval 调度边界，但不实现完整分布式 scheduler。
- 定义 `PluginRun` 最小状态字段：`queued`、`running`、`succeeded`、`failed`、`timeout`、`cancelled`。
- 定义 run 审计字段：`run_id`、`plugin_id`、`capability`、`request_id`、`trigger_type`、`started_at`、`finished_at`、`duration_ms`、`output_summary`、`error_summary`、`metadata`。
- 定义 timeout、异常、DTO 校验失败、插件结构化错误和空结果的处理语义。
- 明确插件不负责调度，不启动后台循环；平台负责 config/effective_config 注入、状态记录和后续恢复。

## 非目标

- 不实现完整分布式 scheduler、独立 scheduler 服务、多 worker 分发或持久化队列。
- 不实现复杂 retry/backoff/rate limit/circuit breaker。
- 不实现 RawEvent 入库、Event Bus 发布或 SourceBinding 全量模型。
- 不实现前端调度配置 UI。
- 不把 FastAPI request 生命周期变成长期调度执行器。
- 不新增真实外部网络调用、真实凭证或生产调度行为。

## 影响范围

- 后续实现主要落在 `packages/core`，新增 scheduling/service/model 边界并复用 Registry 与 Runtime V1。
- 如需 API 暴露，`apps/api` 只能作为薄 HTTP trigger 边界，不承载调度循环或核心执行逻辑。
- Plugin SDK 不新增 scheduler 能力；插件仍只实现 Runtime Protocol / capability DTO。
- 本 change 不要求更改 `BasePlugin`，也不要求 RuntimeService 写 capability 分支。

## 风险边界

- 过早实现完整 SourceBinding 会扩大范围；V1 先用 `plugin_id + capability + effective_config + input` 表达一次 run。
- 只做内存 run 记录会限制重启恢复；V1 可以先定义持久化字段和 storage port，实际落地允许最小内存 repository 作为 test harness。
- interval 调度如果直接挂在 API 进程会引入生命周期风险；V1 只定义 worker/scheduler 运行边界，API 只发起手动 trigger 或配置请求。
