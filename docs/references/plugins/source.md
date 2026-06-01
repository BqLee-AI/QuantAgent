# Source 插件参考

本文档是当前仓库里 `source` 插件的实现与集成参考，面向实现者、reviewer 和后续 issue 承接者。它说明现在已经落地的运行机制、平台边界、`effectiveConfig` 合同、兼容约束，以及后续如何接入正式 `SourceBinding`。

## 1. Source 插件运行机制

当前 `source` 插件统一通过：

- `plugin.yaml` 声明 `id`、`type=source`、`entrypoint`、`capabilities`、`config_schema`
- `packages/core` 的 Registry 扫描与校验
- `PluginRuntimeService` 按 manifest entrypoint 加载与调用
- `PluginSchedulingService` 作为平台触发边界，把 `effective_config` 和 `input` 送进 runtime

现阶段真正稳定的 source 能力入口是：

- `source.fetch`

个别插件为了兼容已有语义也暴露了：

- `source.search`
- `source.extract`

但这些仍必须通过同一套 Runtime DTO / `PluginInvokeRequest` / `SourceFetchResult` 边界走，不允许插件自己扩出第二套 host 协议。

## 2. 平台如何加载和调用 source 插件

当前调用链是：

```text
plugin.yaml
  -> PluginRegistry
  -> PluginSchedulingService.trigger()
  -> PluginRuntimeService.invoke()
  -> RuntimeContext.config + PluginInvokeRequest.input
  -> source plugin.invoke()
  -> SourceFetchResult
```

职责分层：

- Registry 只做发现、manifest 校验、schema 路径确认和记录状态。
- Runtime 只做 entrypoint 加载、生命周期调用和插件协议隔离。
- Scheduling 只做 trigger、run 记录、失败归因、超时控制和后续事件发布桥接。
- source 插件只消费平台传入配置并返回标准化结果。

插件不负责：

- `RawEvent` 入库
- 去重
- `SourceBinding` 管理
- Event Bus 发布
- scheduler loop
- 权限、审计、生命周期托管

## 3. 配置来源与 `effectiveConfig`

`source` 插件的配置来源现在已经收口为平台合同，而不是“插件自己 merge”：

```text
source defaults
  + config template asset
  + binding override
  = EffectiveSourceConfig snapshot
  -> runtime flatten config
  -> plugin context.config
```

本仓库已经落地的核心对象在 `packages/core/src/quantagent/core/source_binding/`：

- `SourceBindingTemplate`
- `EffectiveSourceConfig`
- `ResolvedSourceExecutionConfig`
- `EffectiveSourceConfigComposer`

字段语义：

- `SourceBindingTemplate`
  描述控制面或行业包“想怎么引用这个 source”。
- `EffectiveSourceConfig`
  是平台合成后的可审计快照，包含 `config`、policy、`config_fingerprint`、`template_refs`、`validated_at`。
- `ResolvedSourceExecutionConfig`
  只在 runtime 内部短暂存在；允许把 `secret_ref` 解引用成真正执行值，但不能作为持久化或公开 API 真源。

关键约束：

- 平台拥有 merge 规则，不允许插件、scheduler、API 或 persistence 各自重算。
- `schedule_policy`、`retry_policy`、`rate_limit_policy` 与 source-specific `config` 分层保存，不平铺进插件私有配置。
- secret 在快照层只以 `secret_ref` 存在，不允许持久化明文。

## 4. 当前无 SourceBinding 时的兼容说明

当前仓库还没有正式 `SourceBinding` 持久化模型与 scheduler loop，因此存在一层兼容适配：

- `PluginTriggerRequest.effective_config` 仍是调度入口字段。
- 如果它传入的是新 `EffectiveSourceConfig` 快照，`PluginSchedulingService` 会先校验其中的 `source_plugin_id` 与当前目标插件一致，再在调用 `source` 插件前提取其中的 `config`，把它适配成旧插件仍能读取的扁平 `context.config`。
- 对结构化 `secret_ref`，平台只在真正 runtime invoke 前做短暂解引用；当前兼容层只支持 `env://<ENV_NAME>` 形式，不会把解引用后的明文回写到快照、审计或 API 输出。
- 如果传入的还是旧形态扁平配置，平台保持原样透传。

为什么必须这样做：

- 现有 `rss-source`、`readability-source`、`tavily-source` 都还把 `self.context.config` 当成“插件专属扁平配置”读取。
- 这次实现只先落地合同边界，不能顺手把所有 source 插件和下游 issue 一次性改造成正式 `SourceBinding` 全链路。

这意味着当前兼容层的真实行为是：

- 平台内部可以开始生产和校验 `EffectiveSourceConfig`
- 已有 source 插件不需要立刻知道 `config_fingerprint` / `template_refs`
- 插件看到的仍是纯插件配置对象，而不是平台快照全文

## 5. 未来接入 SourceBinding 的方式

后续接入正式 `SourceBinding` 时应遵守以下顺序：

1. `#216` 把 `EffectiveSourceConfig` 快照映射到持久化层。
2. `#217` 让 scheduler 直接消费该快照和 policy 对象，不再自行 merge。
3. `#225` 让行业包模板目录映射到 `config_template_ref` / `config_override` / policy hint。
4. `#226` 只暴露脱敏 summary、fingerprint 和允许动作，不直接公开运行时解密结果。

必须避免的做法：

- 在 scheduler loop 里重新拼 defaults/template/override
- 在 API handler 里定义另一套 `effective_config` 字段
- 让插件自己读模板文件或 secret store
- 把 resolved secret 回写到 ORM / 审计 / API 响应

## 6. 如何开发一个新的 source 插件

最小交付物：

- `plugins/sources/<plugin-name>/plugin.yaml`
- `plugins/sources/<plugin-name>/config.schema.json`
- `plugins/sources/<plugin-name>/README.md`
- 插件入口实现
- 最小测试

开发规则：

- 插件类型固定为 `source`
- 默认能力优先实现 `source.fetch`
- 配置约束只通过 `config.schema.json` 声明
- 运行时只读 `self.context.config` 和 `request.input`
- 输出统一为 `SourceFetchResult`
- 需要中文注释时，只写非显然边界原因，不写流水账

最小骨架示例：

```python
from quantagent.plugin_sdk import (
    BasePlugin,
    PluginInvokeRequest,
    PluginInvokeResult,
    PluginRuntimeError,
    SourceFetchResult,
    SourceItemDraft,
)


class ExampleSourcePlugin(BasePlugin):
    async def invoke(self, request: PluginInvokeRequest) -> PluginInvokeResult:
        if request.capability != "source.fetch":
            raise PluginRuntimeError(
                code="PLUGIN_CAPABILITY_NOT_IMPLEMENTED",
                message="Example source only implements source.fetch.",
                stage="invoke",
                details={"capability": request.capability},
            )

        config = dict(self.context.config)
        item = SourceItemDraft(
            title="Example title",
            url=config.get("url"),
            content="example content",
            metadata={"plugin_id": self.context.plugin_id},
        )
        result = SourceFetchResult(items=(item,), metadata={"source": "example"})
        return PluginInvokeResult(output=result.to_mapping())


plugin = ExampleSourcePlugin
```

`plugin.yaml` 最小示例：

```yaml
id: quantagent.official.source.example
name: Example Source
type: source
version: 0.1.0
entrypoint: src.example_source:plugin
capabilities:
  - source.fetch
config_schema: config.schema.json
```

`config.schema.json` 最小示例：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Example Source Config",
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "pattern": "^https?://",
      "minLength": 1
    }
  },
  "required": ["url"],
  "additionalProperties": false
}
```

## 7. 常见误区

- 误区：在插件里自己实现后台轮询。
  实际：pull source 必须由统一 scheduler 管理。

- 误区：把 `request.input` 当成配置真源，并覆盖所有平台治理字段。
  实际：`request.input` 只适合表达单次调用输入；平台长期配置应来自 `effective_config`。

- 误区：把 API key、cookie、authorization header 明文放进插件配置快照。
  实际：应保留 `secret_ref`，只在 runtime 内部解引用。

- 误区：把 `schedule_policy`、`retry_policy` 平铺进 source-specific config。
  实际：策略对象属于平台治理字段，应独立表达。

- 误区：source 插件直接返回自定义 dict。
  实际：必须返回 `SourceFetchResult`，并保证可被 `SourceFetchResult.from_mapping(...)` 重建。

- 误区：在插件里顺手做 `RawEvent` 入库、去重或 Event Bus 发布。
  实际：这些都属于平台侧流程，不属于 source 插件职责。

## 8. 当前插件示例

当前官方 source 插件可作为实现参考：

- `plugins/sources/rss-source`
  只读平台传入配置，不允许 `request.input` 覆盖 feed 列表。
- `plugins/sources/readability-source`
  读取单 URL 页面正文，使用受控 `opener` seam 做测试。
- `plugins/sources/tavily-source`
  兼容 `source.fetch` / `source.search` / `source.extract` 语义，但仍收敛到统一 DTO。

如果新插件需要 reader fallback、外部搜索服务或 vendor client，也应把这些能力封装在插件内部，而不是把第三方实现上升成 core 依赖。
