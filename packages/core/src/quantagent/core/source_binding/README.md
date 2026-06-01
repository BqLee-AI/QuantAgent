# source_binding

`quantagent.core.source_binding` 是 SourceBinding Template 与 Effective Config 的平台侧合同边界。

它只负责：

- 归一化 `SourceBindingTemplate`
- 表达 `EffectiveSourceConfig`
- 校验 schedule / retry / rate-limit policy hint
- 合成 source defaults、template asset、inline override
- 保留可审计快照与运行时 secret 解引用边界

它不负责：

- `SourceBinding` ORM / migration / repository
- scheduler loop、重试执行器或 Event Bus 发布
- source 插件实现细节
- API DTO 或前端表单协议

三层对象边界：

- `SourceBindingTemplate`
  行业包或控制面声明层，只描述引用和覆盖意图。
- `EffectiveSourceConfig`
  平台合成后的可审计快照，可被 scheduler / persistence / API 读取。
- `ResolvedSourceExecutionConfig`
  仅 runtime 内部短暂存在；允许把 `secret_ref` 解引用成实际值，但不能回写为持久化或公开输出。

兼容说明：

- 当前仓库已有 source 插件仍普遍把 `context.config` 当成“扁平插件配置”读取。
- 因此平台在真正调用 source 插件前，会从 `EffectiveSourceConfig` 中取出 `config` 作为运行时配置，保证旧插件不因新快照结构破坏。
- policy、fingerprint、template refs 和 `validated_at` 仍留在平台侧，不直接塞给插件。
