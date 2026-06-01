# 插件底座 Demo：从 Registry 到 Scheduling

本文说明当前第一版插件底座如何工作，并用 `plugins/sources/placeholder-source` 这个最小可运行参考插件串起完整链路。

这个 demo 不是生产 RSS 插件，也不是后续 source 插件的业务模板。它的作用是让维护者和后续插件作者能看清：

```text
plugin.yaml -> Registry -> Runtime -> Scheduling -> PluginRunRecord
```

它证明的是“插件可以被发现、加载、调用、审计”，不证明“RSS 已经可用”或“事件主链路已经完成”。

## 1. Demo 插件在哪里

```text
plugins/sources/placeholder-source/
  plugin.yaml
  config.schema.json
  placeholder_source.py
  README.md
```

`plugins/` 是官方随代码分发插件目录。这里的 placeholder 插件会被 Registry 当作官方插件扫描出来，但它只用于本地冒烟验证和开发参照，不承载真实业务数据源。

## 2. Manifest 是登记真源

`plugin.yaml` 描述插件身份、能力和入口：

```yaml
id: quantagent.official.source.placeholder
name: Demo Placeholder Source
type: source
version: 0.1.0
entrypoint: placeholder_source:plugin
description: Minimal runnable source plugin used to validate the plugin foundation.
capabilities:
  - source.fetch
config_schema: config.schema.json
```

关键点：

- `id` 是全局插件 ID。
- `type: source` 表示它是数据源插件。
- `capabilities` 声明它能响应 `source.fetch`。
- `entrypoint` 指向插件目录里的 Python class/factory。
- `config_schema` 只描述配置形态，不保存用户配置值。

## 3. Registry 负责发现和校验

Registry 不猜测插件用途，只扫描目录里的 `plugin.yaml`：

```text
RegistryScanner.scan()
  -> 扫描 plugins/ 和 runtime/plugins/
  -> 找到 plugin.yaml
  -> 校验必填字段、type、capabilities 和 config.schema.json
  -> 返回 PluginRecord
```

对 placeholder 插件，Registry 会得到：

```text
PluginRecord
  id = quantagent.official.source.placeholder
  source = official
  status = valid
  path = plugins/sources/placeholder-source
  manifest.capabilities = ("source.fetch",)
```

Registry V1 的 API 查询仍然只负责展示和诊断插件登记信息，不负责业务调度。

## 4. Runtime 负责加载和调用插件

Runtime 从 `PluginRecord` 出发加载 manifest entrypoint：

```text
PluginRuntimeService.invoke(record, capability="source.fetch", ...)
  -> 根据 record.path 定位插件目录里的 entrypoint 文件
  -> 用隔离模块名加载 placeholder_source:plugin
  -> 创建插件实例
  -> 注入 RuntimeContext
  -> 调用 load/start/invoke/stop
  -> 返回 PluginRuntimeInvocation
```

插件代码只读取平台传入的 `input` / `config` / `context`，并返回标准 output：

```python
query = request.input.get("query") or self.context.config.get("query") or "placeholder"
output = SourceFetchResult(...)
return PluginInvokeResult(output=output.to_mapping())
```

RuntimeContext 是受控上下文，默认不暴露 DB session、scheduler、Event Bus 或内部 service。

这条边界很重要：插件只交回能力产物，平台侧持久化、调度、审计和事件分发不能下放给插件自行处理。

## 5. Scheduling 负责编排和审计

Scheduling 在 Runtime 之上统一触发插件能力并记录 run：

```text
PluginSchedulingService.trigger(request)
  -> 二次校验 PluginTriggerRequest
  -> Registry.get_plugin(plugin_id)
  -> 创建 queued run
  -> 标记 running
  -> Runtime.invoke(...)
  -> 写入 succeeded / failed / timeout
  -> 返回 PluginRunRecord
```

对 placeholder 插件，最小请求可以是：

```text
PluginTriggerRequest
  plugin_id = quantagent.official.source.placeholder
  capability = source.fetch
  request_id = req-placeholder-smoke
  trigger_type = manual
  input = {"query": "rss"}
  effective_config = {}
  metadata = {"origin": "foundation-smoke"}
```

成功后会得到：

```text
PluginRunRecord
  status = succeeded
  plugin_id = quantagent.official.source.placeholder
  request_id = req-placeholder-smoke
  metadata.origin = foundation-smoke
  output_summary.items[0].external_id = placeholder:rss
```

`output_summary` 是审计摘要，不等于后续业务入库。RawEvent 入库、去重和 Event Bus 发布属于后端 ingestion/pipeline 层，不属于这个 demo。

## 6. 本地验证命令

从仓库根目录运行插件底座相关测试：

```bash
PYTHONPATH=packages/core/src:packages/plugin-sdk/src python -m unittest packages.core.tests.test_plugin_foundation_demo packages.core.tests.test_scheduling packages.core.tests.test_runtime packages.core.tests.test_registry
```

其中 `packages/core/tests/test_plugin_foundation_demo.py` 用三个小测试展示 demo 链路：

```text
真实 plugins/ 目录
  -> RegistryScanner
  -> PluginRegistry
  -> PluginRecord
  -> PluginSchedulingService.trigger
  -> PluginRuntimeService.invoke
  -> placeholder_source:plugin
  -> PluginRunRecord history
```

这个测试不需要数据库、API、Web、worker 或网络。

如果只想看 demo 的分阶段小测试，可以运行：

```bash
PYTHONPATH=packages/core/src:packages/plugin-sdk/src python -m unittest packages.core.tests.test_plugin_foundation_demo
```

这个测试会扫描真实 `plugins/` 目录，但使用一个不存在的 `runtime/` 测试目录，避免把本机私有插件混进验证结果。测试运行时会用中文打印每个阶段“是否实现、怎么实现、验证结果和边界说明”，方便 reviewer 跟着输出理解当前插件底座能力。

## 7. 这个 Demo 不做什么

这个 demo 有意不做：

```text
真实 RSS 抓取
RawEvent / SourceItem 入库
Event Bus 发布
SourceBinding 管理
worker/scheduler loop
后台轮询
交易、审批或策略判断
```

后续如果要实现 `RSS -> 入库 -> Event Bus -> 分析 -> 通知/审批/交易`，应在后端 ingestion、pipeline、worker、approval 和 broker 边界继续推进，而不是让 source 插件直接持有数据库或内部 service。

换句话说，真实 RSS 插件后续只应该负责抓取和标准化 RSS item；平台接收 `SourceFetchResult` 之后，再由后端 service/repository/event bus 完成入库、去重和事件流转。

## 8. 插件作者可以照着做什么

新插件最小结构：

```text
my-plugin/
  plugin.yaml
  config.schema.json
  my_plugin.py
```

实现原则：

- 用 `plugin.yaml` 声明 ID、类型、能力和 entrypoint。
- 用 `config.schema.json` 声明配置契约。
- 插件类可以继承 `BasePlugin`，但 Runtime 只要求满足协议。
- `source.fetch` 插件返回 `SourceFetchResult` 形状。
- 插件只返回 DTO，不直接写 DB、不发 Event Bus、不自己跑 while loop。
- 需要真实外部请求、依赖、secret 或 rate limit 时，在具体插件 issue / OpenSpec 中单独说明，不塞进这个 placeholder demo。
