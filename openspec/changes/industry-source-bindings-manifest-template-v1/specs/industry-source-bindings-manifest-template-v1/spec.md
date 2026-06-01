## ADDED Requirements

### Requirement: 行业包 manifest 必须显式声明 source_bindings 元信息

QuantAgent SHALL 要求行业包 `plugin.yaml` 通过 `source_bindings` 条目显式声明 source 依赖元信息，而不是把这些绑定散落在任意 YAML、README 或代码常量中。

#### Scenario: manifest 声明 required 与 optional source
- **WHEN** 一个行业包需要依赖多个 source 插件
- **THEN** 它的 `plugin.yaml` 使用 `source_bindings` 列表声明每个 `source_plugin_id`
- **AND** 每个条目显式标记 `required: true` 或 `required: false`

#### Scenario: manifest 条目保持最小可读字段
- **WHEN** 维护者审查行业包 `source_bindings`
- **THEN** 每个条目至少包含 `source_plugin_id`、`required` 和 `config_template`
- **AND** manifest 不要求把大段 source-specific override 内联写入同一条目

### Requirement: config_template 必须指向插件内模板目录

QuantAgent SHALL 将行业包 `source_bindings[*].config_template` 定义为指向插件根目录内模板文件的相对路径。

#### Scenario: 默认目录使用 templates/source_bindings
- **WHEN** 行业包为某个 source 声明默认 override 模板
- **THEN** `config_template` 默认指向 `templates/source_bindings/` 下的 YAML 文件
- **AND** 模板文件落在行业包插件目录内

#### Scenario: 路径使用相对插件根目录的引用
- **WHEN** `plugin.yaml` 声明 `config_template`
- **THEN** 该值是相对插件根目录的路径
- **AND** 它不依赖绝对路径、跨插件路径或运行时生成路径

#### Scenario: 模板命名表达 source 与用途
- **WHEN** 行业包创建 source binding 模板文件
- **THEN** 模板文件名采用 `<source-name>.<purpose>.yaml` 风格
- **AND** 维护者可以从文件名判断模板对应的 source 和用途

### Requirement: 行业包模板只表达 template 层配置

行业包 `source_bindings` 模板 SHALL 只表达行业包对 source 的默认 override，不得承载 effective config、运行态状态或 secret 明文。

#### Scenario: 模板不承载运行态字段
- **WHEN** 行业包编写 `templates/source_bindings/*.yaml`
- **THEN** 模板不包含 `binding_id`、`effective_config`、`status`、`last_run_at`、`next_run_at` 或运行结果统计字段
- **AND** 这些字段留给后续 core contract 或 persistence change

#### Scenario: 模板不承载 secret 明文
- **WHEN** 模板需要表达敏感配置
- **THEN** 模板不得存放真实 secret、token、私有账户或生产凭证明文
- **AND** 敏感信息只允许以后续 contract 定义的 reference 方式接入

### Requirement: README 必须解释 source_bindings 资产边界

行业包 SHALL 提供最小 README / usage note，解释 `source_bindings` 模板用途、required/optional 语义和禁止写入内容。

#### Scenario: README 解释模板用途与依赖语义
- **WHEN** 维护者阅读行业包 README
- **THEN** README 说明每个 source binding 模板的用途
- **AND** README 说明哪些 source 是 required，哪些是 optional

#### Scenario: README 解释与 core change 的职责分离
- **WHEN** README 描述 `source_bindings`
- **THEN** README 明确 effective config 合成由后续 contract change 负责
- **AND** README 明确持久化和调度运行状态由后续 persistence / scheduler change 负责

### Requirement: V1 必须提供最小行业包样例骨架

QuantAgent SHALL 为后续行业包实现提供一个最小样例骨架，用于展示 `source_bindings` 的目录组织和降级语义。

#### Scenario: 样例包含 required source 与 optional source
- **WHEN** 维护者参考 V1 行业包样例
- **THEN** 样例至少包含一个 `required` source binding 和一个 `optional` source binding
- **AND** 两者分别引用各自的模板文件

#### Scenario: 样例文件结构可直接复用
- **WHEN** 后续行业包实现开始创建插件资产
- **THEN** 样例展示 `plugin.yaml`、`README.md` 和 `templates/source_bindings/*.yaml` 的最小组合
- **AND** 实现者不需要再自行发明新的模板目录结构

### Requirement: 行业包 source_bindings 约定不得反向定义其他层真源

本 change SHALL 只约束行业包资产层，不反向定义 source plugin 实现、effective config 合成算法或持久化模型。

#### Scenario: 不替代 source plugin issue
- **WHEN** 行业包样例引用 RSS 或 reader source
- **THEN** 样例只声明 `source_plugin_id` 和模板引用
- **AND** 它不定义 RSS、Readability、Jina 等 source 插件的运行逻辑或输出 DTO

#### Scenario: 不替代 effective config 与 persistence change
- **WHEN** 后续实现需要计算 effective config、创建 SourceBinding 记录或保存 SchedulerRun 状态
- **THEN** 实现复用独立的 contract / persistence change
- **AND** 不把这些字段直接扩回行业包 manifest 或模板文件
