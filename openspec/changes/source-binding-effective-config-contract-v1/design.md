## Context

`docs/design/06-source-plugin-design.md` 已把 `SourceBinding` 定义为 pull source 的调度主对象，并要求平台负责 “source default config + industry source binding override = effective source config”。`docs/design/07-industry-package-design.md` 又要求行业包通过 `source_bindings` 声明 source 依赖；`docs/design/11-crawler-source-plugin-boundary.md` 明确插件只消费平台传入的 DTO / `effective_config`，不负责配置保存、调度、审计或 secret 管理。

当前缺口不在“要不要有 effective config”，而在“effective config 究竟是什么对象、哪些字段属于哪一层、由谁生成、谁可以持久化和谁只能短暂消费”。如果这一层不先定义，`#216` 会把持久化模型当契约真源，`#217` 会把 scheduler 输入当契约真源，`#225` 会把行业包模板资产当契约真源，`#226` 则容易把 API DTO 误当成平台内部配置对象。

本 change 只定义跨模块契约，不落任何实现代码。后续实现仍需遵守依赖方向 `apps/api -> packages/core -> packages/plugin-sdk <- plugins/*`，并保持插件只通过 `plugin-sdk` 消费运行时输入。

## Goals / Non-Goals

**Goals:**

- 定义平台归一化后的 `SourceBindingTemplate` 最小字段和禁止写入内容。
- 定义平台合成后的 `EffectiveSourceConfig` 快照字段、来源层级、合并优先级和校验入口。
- 固定三层配置边界：模板层、可审计快照层、runtime secret 注入执行层。
- 固定 `schedule_policy`、`retry_policy`、`rate_limit_policy` 与 source-specific `config` 的分层关系。
- 指定未来实现的目录蓝图、责任分层、失败路径和验证入口，让 `#216/#217/#225/#226` 在同一真源上继续推进。

**Non-Goals:**

- 不定义 `SourceBinding` / `SchedulerRun` ORM、migration、repository 或 service 实现细节。
- 不定义 scheduler loop、并发控制、重试器或 Event Bus 发布行为。
- 不定义行业包模板目录结构、文件命名或样例资产；这些留给 `#225`。
- 不定义 REST DTO、动作路径或 Web 页面；这些留给 `#226`。
- 不把 secret 解引用后的执行对象作为持久化或公开 API 契约。

## Directory And Ownership Blueprint

本 change 只写 OpenSpec，但后续实现应围绕以下边界收敛：

```text
packages/core/src/quantagent/core/source_binding/
  template_models.py          # SourceBindingTemplate、policy hint、secret ref 等平台侧契约
  template_loader.py          # 行业包 manifest / template 资产 -> 平台归一化模板
  effective_config.py         # 合成、schema 校验、fingerprint 与审计快照生成
  policy_models.py            # schedule/retry/rate-limit policy 的平台侧校验对象
  README.md                   # 说明模板层、快照层、运行时注入层的职责边界

packages/plugin-sdk/src/quantagent/plugin_sdk/dto.py
  # 复用既有 source runtime 输入 DTO 承接 validated effective_config，
  # 不新增插件可直接调用的合成器或 secret resolver

packages/core/tests/source_binding/
  test_template_loader.py
  test_effective_config.py
```

选择 `packages/core` 而不是 `packages/contracts` 的原因：

- 当前消费者主要是 Python runtime、scheduler、persistence 和插件运行时，而不是已经确定的跨语言生成链。
- 该契约既包含平台治理规则，也包含 secret / audit / merge 语义，不只是单纯字段定义。
- 在没有明确 schema 源头、生成命令和 TS 消费方前，不提前把它抽成 `packages/contracts`。

## Core Model Drafts

### 1. SourceBindingTemplate

`SourceBindingTemplate` 是平台归一化后的模板对象，不等同于行业包 manifest 原始条目，也不等同于数据库模型。

```text
SourceBindingTemplate
  source_plugin_id: string
  required: boolean
  config_template_ref: string | null
  config_override: object
  schedule_policy_hint: object | null
  retry_policy_hint: object | null
  rate_limit_policy_hint: object | null
  metadata: object
```

字段约束：

- `source_plugin_id` 必填，对应一个通过 Registry 可发现的 source 插件。
- `required` 表示行业包依赖强度；降级语义由后续行业包 / scheduler / API issue 继续定义。
- `config_template_ref` 是模板引用标识，只表达“引用哪份模板资产”，不在本 change 中绑定目录路径规则；目录组织留给 `#225`。
- `config_override` 是 JSON-safe override object，用于表达模板内联覆盖，不承接运行时状态、ORM id、审计字段或 secret 明文。
- `schedule_policy_hint`、`retry_policy_hint`、`rate_limit_policy_hint` 只保存平台可审计的策略提示，不与 source-specific `config_override` 平铺混写。
- `metadata` 只允许 JSON-safe 说明性字段；不能承接 request id、run status、next_run_at 或插件执行结果。

### 2. EffectiveSourceConfig

`EffectiveSourceConfig` 是平台完成合并与 schema 校验后的稳定快照，可被持久化、审计和 scheduler/runtime 读取，但其中不包含解引用后的 secret 明文。

```text
EffectiveSourceConfig
  source_plugin_id: string
  config: object
  schedule_policy: object | null
  retry_policy: object | null
  rate_limit_policy: object | null
  config_fingerprint: string
  source_schema_version: string | null
  template_refs: object
  validated_at: string
  metadata: object
```

字段约束：

- `config` 只保存 source-specific 配置结果，且仍可能包含 `secret_ref` 占位对象。
- 三类 policy 对象独立于 `config` 保存，便于 scheduler、持久化和 API 各自消费而不重新拆字段。
- `config_fingerprint` 由平台根据校验后的快照计算，用于审计、缓存失效和后续 run 归因。
- `source_schema_version` 记录合成时采用的 source schema 版本；如果插件未声明独立 schema version，可以为空。
- `template_refs` 用于记录参与合成的模板引用和层来源，不承接目录路径语义或运行时 secret 值。
- `validated_at` 记录平台完成校验的时间戳。

### 3. Runtime-Resolved Execution Config

运行时 secret 注入对象不是本 change 的稳定公开契约，只是 runtime 内部短暂存在的执行层：

```text
ResolvedSourceExecutionConfig
  # 仅 runtime 内部使用，不持久化、不审计、不直接公开给 API
  config: object  # secret refs 已解引用
  schedule_policy: object | null
  retry_policy: object | null
  rate_limit_policy: object | null
```

这一层存在的原因是：`EffectiveSourceConfig` 必须可审计且不能含 secret 明文，但 source plugin 执行时又需要真正可用的凭证、token 或 header 值。

## Data Flow And Validation

### 合成输入

```text
source plugin defaults
  + config_template_ref 指向的模板资产
  + SourceBindingTemplate.config_override
  + policy hints
  -> EffectiveSourceConfig
  -> runtime secret resolution
  -> plugin invoke
```

### 合并优先级

1. source 插件声明的默认配置
2. `config_template_ref` 对应模板资产内容
3. `config_override`
4. 平台生成字段（`config_fingerprint`、`validated_at`、`template_refs` 等）

约束：

- 平台生成字段不进入 `config`，也不允许被 override 覆盖。
- policy 对象不参与 source-specific `config` 的 key merge，而是独立校验、独立持久化、独立传递。
- `null` 只有在插件 schema 或 policy schema 明确允许时才可用于覆盖。

### 校验入口

- template loader 先校验 `SourceBindingTemplate` 自身结构、JSON-safe 约束和顶层未知字段。
- effective config composer 再按 source 插件 `config.schema.json` 和平台 policy schema 校验合并结果。
- 若插件 schema 未声明某字段且没有显式允许附加字段，则将未知 override 视为校验失败，而不是静默保留。
- runtime secret resolver 只接受 `secret_ref` 占位对象；若发现 literal secret 值进入敏感字段，必须拒绝进入运行时层。

## Decisions

### Decision 1: 使用“模板层 + 快照层 + 运行时注入层”三层模型

原因：

- issue #215 的验收口径要求明确区分模板层、effective config 层和 runtime secret 注入层。
- 只保留模板层和运行时层会让持久化、审计和 scheduler 缺少稳定真源。
- 只保留模板层和快照层则无法解释插件运行时如何安全拿到 secret。

备选方案与取舍：

- 方案 A：只定义一个大 JSON blob。缺点是无法表达来源层级、审计边界和 secret 注入点，拒绝采用。
- 方案 B：把 secret 解引用结果直接写入 `EffectiveSourceConfig`。缺点是违反 secret reference 约束，也会污染持久化和 API，拒绝采用。

### Decision 2: `config_template_ref` 只定义为“引用标识”，不在本 change 中绑定目录约定

原因：

- issue #225 明确负责行业包 `source_bindings` manifest/template 的目录和样例。
- 本 change 的职责是定义跨模块契约，不应把文件路径组织细节写死在 core contract 中。

备选方案与取舍：

- 方案 A：在这里直接规定 `templates/source_bindings/*.yaml`。这会抢占 `#225` 的范围，拒绝采用。
- 方案 B：完全不保留模板引用字段。这样无法描述行业包资产如何参与合成，拒绝采用。

### Decision 3: policy 对象与 source-specific `config` 分离

原因：

- scheduler、持久化和 API 需要直接读取 schedule/retry/rate-limit 语义。
- 平铺在 `config` 中会让不同 source 插件、不同 API DTO 和持久化模型各自重新命名这些字段。

备选方案与取舍：

- 方案 A：所有策略字段都放进 `config`。会增加 source schema 与 scheduler 行为的耦合，拒绝采用。
- 方案 B：把策略对象完全延后到 `#216/#217`。会让这些 issue 重新发明字段命名，拒绝采用。

### Decision 4: unknown override 默认拒绝，而不是保留原样

原因：

- 该契约是平台治理边界，不接受“随便塞一个 key 以后再说”的隐式扩展。
- 默认拒绝能更早暴露行业包模板与 source schema 的不匹配问题。

备选方案与取舍：

- 方案 A：未知字段静默透传。实现快，但后续 API、审计和持久化无法判断字段来源，拒绝采用。
- 方案 B：只记录 warning 继续运行。会让不同环境出现不同 effective config 结果，拒绝采用。

### Decision 5: 插件只消费 platform-generated effective config，不参与合成或 secret 解引用策略决定

原因：

- `plugins/AGENTS.md` 与 `docs/design/11-crawler-source-plugin-boundary.md` 都要求插件只消费平台传入 DTO / `effective_config`。
- 让插件自己合并 override 或自己读 secret，会破坏 core/runtime/registry 的治理边界。

备选方案与取舍：

- 方案 A：插件在 `invoke()` 内读取 schema 默认值并自行 merge。违反平台治理原则，拒绝采用。
- 方案 B：scheduler 或 API 各自重算 effective config。会造成多真源，拒绝采用。

## Risks / Trade-offs

- [Risk] 三层对象会增加实现者理解成本。  
  → Mitigation：在 `packages/core/src/quantagent/core/source_binding/README.md` 中固定每层职责和“不要放什么”。

- [Risk] 过早定义过多字段会压缩后续演进空间。  
  → Mitigation：本 change 只定义 issue #215 验收所需的最小字段和元数据，不引入 owner、run 状态或 API 专用字段。

- [Risk] `config_template_ref` 仅为引用标识，目录规则尚未在本 change 中冻结。  
  → Mitigation：在 `#225` 中继续收口模板目录与样例，但要求其只映射到本 change 的字段，不改动合成语义。

- [Risk] 默认拒绝未知字段会增加接入成本。  
  → Mitigation：把失败点前移到模板加载 / 合成校验阶段，减少运行时漂移和审计不确定性。

## Migration Plan

1. 先以本 change 提交 OpenSpec-only PR，并获得维护者明确评论“没问题”或批准。
2. `#216` 基于本 change 定义 `SourceBinding` / `SchedulerRun` 的持久化字段与 repository 边界，但不得把 runtime-resolved secret 写入 ORM。
3. `#217` 基于本 change 让 scheduler 读取持久化的 `EffectiveSourceConfig` 快照和 policy 对象，不再重算 merge。
4. `#225` 只定义行业包资产目录与样例，映射到 `config_template_ref` / `config_override` / policy hint，不改变合成语义。
5. `#226` 只暴露脱敏 summary 与动作边界，不公开 runtime secret 或内部快照原文。

## Open Questions

- V1 是否需要统一 `SecretValueRef` 的具体 JSON 结构，例如 `{"secret_ref": "env://FOO"}` 与更复杂的带 metadata 形式；本 change 先只要求“结构化 secret reference”，具体字段可在实现 PR 固定。
- source 插件默认配置的真源是否完全来自 `config.schema.json` 的默认值，还是允许未来 manifest 补充默认块；本 change 先只要求“source plugin defaults”作为最低优先级输入。
- 后续若出现非行业包 owner（例如 runtime private binding），是否需要扩展模板 metadata；这不影响本 change 的 effective config 合成契约。
