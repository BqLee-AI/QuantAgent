## 背景

行业包是 `industry` 类型插件，但它既不是 runtime，也不是持久化模型。`source_bindings` 在行业包中的职责，应当是声明“本行业包默认依赖哪些 source，以及给这些 source 的模板化覆盖长什么样”，而不是承载 effective config 合成、调度状态或运行结果。

当前真源已经给出三层约束：

- `docs/design/07-industry-package-design.md`：行业包通过 `source_bindings` + `config_template` 声明 source 依赖。
- `docs/design/06-source-plugin-design.md`：平台负责“source default config + 行业包 override = effective config”，并由 Scheduler 围绕 `SourceBinding` 运行。
- `docs/prd/pages/10-plugins-index.md` / `11-plugin-detail.md`：Industry 插件需要在治理界面中展示 `SourceBinding`、依赖和提供能力。

因此，本 change 只定义行业包资产层的目录、文件职责、字段边界和样例，不触碰平台执行层。

## 目标与非目标

**目标：**

- 固定行业包 `source_bindings` 的默认资产布局，使维护者不需要再讨论模板文件放在哪里。
- 固定 `plugin.yaml` 中 `source_bindings` 条目的最小可读字段，避免 manifest 膨胀为运行时配置 blob。
- 固定 `config_template` 的引用方式、命名风格和相对路径边界。
- 固定 README / usage note 需要解释的职责边界，避免执行者把 secret、runtime 字段或调度状态写进模板。
- 提供一个最小样例骨架，供 RSS / reader 类 source 在行业包侧接入时复用。

**非目标：**

- 不定义 template 字段全集、默认值合并算法、secret 解引用算法或 schema 校验实现。
- 不定义行业包如何被 Registry 展示、如何被 API 返回，除了要求后续实现可稳定读取这些资产。
- 不定义具体行业内容，例如石油、半导体、私有 watchlist 或账户列表。

## 目录与文件规划

后续行业包实现 SHOULD 采用以下最小结构：

```text
plugins/industries/<industry-name>/
  plugin.yaml
  config.schema.json
  README.md
  templates/
    source_bindings/
      rss.default.yaml
      readability.fallback.yaml
```

文件职责：

- `plugin.yaml`
  - 行业包 manifest 真源。
  - 只声明 `source_bindings` 元信息，不承载大量 source-specific override 内容。
- `config.schema.json`
  - 行业包自身配置 schema。
  - 不替代 `source_bindings` 模板文件。
- `templates/source_bindings/*.yaml`
  - 行业包对具体 source 的默认 override 模板。
  - 只表达 template 层字段，不表达运行态字段。
- `README.md`
  - 说明每个模板用途、required/optional 语义、不要写什么、与 #215 / #216 的关系。

本结构服务于两类消费方：

- 人类维护者：可以快速定位 manifest、模板和 usage note。
- 平台实现：后续可以稳定读取 `plugin.yaml` 中的 `config_template` 相对路径，并在插件根目录内解析目标模板。

## Manifest 条目设计

行业包 `plugin.yaml` 中的 `source_bindings` 条目 SHOULD 保持精简，最小字段如下：

```yaml
source_bindings:
  - source_plugin_id: quantagent.official.source.rss
    required: true
    config_template: templates/source_bindings/rss.default.yaml
  - source_plugin_id: quantagent.official.source.readability
    required: false
    config_template: templates/source_bindings/readability.fallback.yaml
```

字段职责：

- `source_plugin_id`
  - 指向被依赖的 source 插件 ID。
- `required`
  - 表达该 source 对行业包是否为阻塞依赖。
- `config_template`
  - 指向插件根目录内的模板文件相对路径。

刻意不放入的内容：

- `effective_config`
- `binding_id`
- `next_run_at`、`last_run_at`
- `status`、`failure_count`
- secret 明文
- runtime 注入字段

原因：这些内容分别属于 #215 的合成结果、#216 的持久化状态或受控 runtime 边界，不应被行业包 manifest 抢占所有权。

## 模板目录与命名约定

### 1. 默认目录

V1 SHOULD 统一使用 `templates/source_bindings/` 作为 `config_template` 的默认根目录。

这样做的原因：

- 避免模板散落在插件根目录或 `src/` 附近，弱化资产边界。
- 与其他可复用资产目录形成一致约定，便于后续扩展更多模板。
- 让 review 和治理 UI 的实现能基于稳定路径约定工作。

### 2. 命名风格

模板文件名 SHOULD 使用 `<source-name>.<purpose>.yaml`，例如：

- `rss.default.yaml`
- `readability.fallback.yaml`
- `jina.reader-default.yaml`

命名目标是让文件名同时回答两个问题：

- 这是哪个 source 的模板。
- 这个模板在行业包里承担什么用途。

### 3. 路径边界

`config_template` 在 V1 SHALL 使用相对插件根目录的路径，且路径必须落在插件目录内。

替代方案包括绝对路径、跨插件路径或 inline YAML blob，但这些方案都会：

- 削弱 manifest 的可移植性。
- 增加路径安全校验负担。
- 让 template 资产难以在插件包内集中审查。

因此本 change 不采用它们作为 V1 主路径。

## README / Usage Note 义务

行业包 README SHALL 至少说明：

- 每个 `source_bindings` 模板的用途。
- 哪些 source 是 `required`，哪些是 `optional`。
- 模板只承载行业包对 source 的默认 override，不承载 effective config 或运行时状态。
- 模板中不得放 secret 明文、私有策略、调度结果、审计字段或运行态计数。
- #215 负责模板层与 effective config 层的字段契约；#216 负责持久化与调度运行状态。

这样做是为了避免目录约定只藏在命名里，符合仓库对复杂能力提供最小 usage note 的长期规则。

## 最小样例骨架

V1 样例 SHOULD 表达“一个 required source + 一个 optional source”的最小组合：

```text
plugins/industries/example-industry/
  plugin.yaml
  README.md
  templates/
    source_bindings/
      rss.default.yaml
      readability.fallback.yaml
```

样例语义：

- `rss.default.yaml`
  - 表达行业包默认订阅的 feed、关键词或过滤条件。
- `readability.fallback.yaml`
  - 表达正文读取增强能力的默认 override。
  - 因为它是 `optional`，缺失时不会阻断行业包主流程。

样例需要回答的不是“字段实现细节”，而是“后续实现时这些资产应如何组织与命名”。

## 数据流与边界

本 change 约束的资产层数据流如下：

```text
industry plugin.yaml
  -> source_bindings metadata
  -> config_template relative path
  -> template file under templates/source_bindings/
  -> platform contract (#215) composes effective config
  -> persistence / scheduler (#216) stores binding and run state
```

边界判断：

- 行业包资产层负责声明意图。
- core contracts 负责定义 template 字段与 effective config 的合成契约。
- persistence / scheduler 负责运行态主对象和历史状态。

## 失败路径

需要在后续实现和 review 中重点防止以下失败：

- `config_template` 指向插件目录外路径。
  - 风险：破坏插件资产封装和路径安全。
- manifest 直接内嵌大量 override 或 runtime 字段。
  - 风险：manifest 膨胀、字段所有权漂移。
- 模板写入 secret 明文或私有策略。
  - 风险：源码泄漏、审计边界失真。
- 不同插件随意使用 `templates/feeds/`、`binding_templates/` 等不同目录。
  - 风险：后续工具、文档和 reviewer 难以统一判断。
- optional source 没有在样例中表达。
  - 风险：后续实现误把所有 source 都当成阻塞依赖。

## 验证策略

本 OpenSpec-only PR 的验证只要求：

- `openspec validate industry-source-bindings-manifest-template-v1 --type change --strict --json` 通过。
- 人工检查 proposal / design / tasks / spec 是否完整覆盖：
  - manifest 条目边界
  - template 目录与命名
  - README 义务
  - required / optional 样例
  - 与 #148 / #215 / #216 的非重叠职责

后续实现阶段的验证再由对应 issue 覆盖，例如：

- 插件包资产可被 Registry 读取。
- `config_template` 路径可被安全解析。
- 样例目录与 README 被实际创建。
