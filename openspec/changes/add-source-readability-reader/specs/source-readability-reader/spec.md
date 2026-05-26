## ADDED Requirements

### Requirement: Official Readability Reader Plugin Package

系统 MUST 支持一个官方 `Readability Link Reader` Source Plugin，作为 `plugins/sources/` 下可分发的插件包交付。

#### Scenario: Official plugin package is defined with minimum deliverables

- **GIVEN** 仓库需要新增官方 `Readability Link Reader` 能力
- **WHEN** 实现者按本 change 落地插件包
- **THEN** 插件包 MUST 包含 `plugin.yaml`、`config.schema.json`、README、入口实现和最小测试
- **AND** 插件 MUST 通过 `plugin.yaml` 注册为 `source` 类型官方插件
- **AND** 插件 `id` MUST 为 `quantagent.official.source.readability`
- **AND** 插件 `capabilities` MUST 至少声明 `source.fetch`

### Requirement: Reader Plugin Consumes Platform-Validated Config

`Readability Link Reader` 插件 MUST 只消费平台传入的校验后配置 DTO / `effective_config`，不负责配置保存或运行时编排。

#### Scenario: Plugin receives URL and request configuration from platform

- **GIVEN** 用户通过控制台或 API 提交了插件配置
- **AND** 平台已经完成 schema 校验和绑定
- **WHEN** 平台调用 `Readability Link Reader` 插件
- **THEN** 插件 MUST 只读取传入的 `url`
- **AND** 插件 MAY 读取可选 `headers` 与 `timeout_seconds`
- **AND** 插件 MUST NOT 自行承担配置保存、启停、调度、审计或生命周期管理

### Requirement: Reader Plugin Returns Source-Contract-Compatible Output

`Readability Link Reader` 插件 MUST 返回符合平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO 的标准结果，而不是引入新的 reader 专用 DTO。

#### Scenario: Plugin extracts article content from a readable page

- **GIVEN** 插件收到了一个可读取的网页 URL
- **WHEN** 插件完成正文抽取
- **THEN** 插件 MUST 返回符合平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO 的标准结果
- **AND** 返回结果 SHOULD 至少包含 URL、正文文本相关字段和必要 metadata
- **AND** 平台随后负责将该结果写入事件链路、持久化并通过 Event Bus 发布

### Requirement: Reader Plugin Boundary Excludes Runtime And Event Responsibilities

`Readability Link Reader` 插件 MUST NOT 承担平台运行时和事件链路职责。

#### Scenario: Plugin capability remains limited to read and normalize

- **GIVEN** 插件被实现为官方 Source Plugin
- **WHEN** 审查插件边界
- **THEN** 插件 MUST 只负责网页抓取、正文抽取、标准化和清晰失败返回
- **AND** 插件 MUST NOT 负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限检查或生命周期托管

### Requirement: Reader Plugin May Encapsulate Third-Party Extraction Dependency

`Readability Link Reader` 插件 MAY 在插件内部封装成熟 Python 开源正文抽取库，但该依赖 MUST 被视为插件实现细节。

#### Scenario: Plugin uses third-party extraction library

- **GIVEN** 实现者为正文抽取选择了成熟 Python 开源库
- **WHEN** 插件完成实现
- **THEN** 该依赖 MUST 只属于插件目录的实现细节
- **AND** 核心系统 MUST NOT 直接耦合、调度或依赖该第三方库
- **AND** 实现 PR MUST 说明依赖用途、许可证边界和最小本地验证方式
