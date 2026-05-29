## ADDED Requirements

### Requirement: Official Jina Reader Plugin Package

系统 MUST 支持一个官方 `Jina Reader` Source Plugin，作为 `plugins/sources/` 下可分发的插件包交付。

#### Scenario: Official plugin package is defined with minimum deliverables

- **GIVEN** 仓库需要新增官方 `Jina Reader` 能力
- **WHEN** 实现者按本 change 落地插件包
- **THEN** 插件包 MUST 包含 `plugin.yaml`、`config.schema.json`、README、入口实现和最小测试
- **AND** 插件 MUST 通过 `plugin.yaml` 注册为 `source` 类型官方插件
- **AND** `plugin.yaml` MUST 声明插件 ID 为 `quantagent.official.source.jina`
- **AND** `plugin.yaml` MUST 声明 `source.fetch` capability

### Requirement: Jina Reader Plugin Consumes Platform-Validated Config

`Jina Reader` 插件 MUST 只消费平台传入的校验后配置 DTO / `effective_config`，不负责配置保存或运行时编排。

#### Scenario: Plugin receives URL and minimal request configuration from platform

- **GIVEN** 用户通过控制台或 API 提交了插件配置
- **AND** 平台已经完成 schema 校验和绑定
- **WHEN** 平台调用 `Jina Reader` 插件
- **THEN** 插件 MUST 只读取传入的 `url`
- **AND** 插件 MAY 读取可选非敏感请求参数与 `timeout_seconds`
- **AND** 插件 MUST NOT 在公开 `config.schema.json` 中声明原始外部 reader token、私有账号或其他敏感鉴权字段
- **AND** 插件 MUST NOT 自行承担配置保存、启停、调度、审计或生命周期管理

### Requirement: Jina Reader Plugin Returns Platform-Defined Source Output

`Jina Reader` 插件 MUST 返回平台约定的 Source Plugin 输出结构 / source runtime 可消费 DTO，而不是引入新的 reader 专用 DTO 或在本 change 中绑定某个 core 内部 DTO 名称。

#### Scenario: Plugin reads a page through external reader service

- **GIVEN** 插件收到了一个允许读取的网页 URL
- **WHEN** 插件通过外部 reader 服务完成内容读取和标准化
- **THEN** 插件 MUST 返回平台约定的 Source Plugin 输出结构
- **AND** 返回结果 MUST 对齐 source runtime 可消费的统一输出契约
- **AND** 返回结果 SHOULD 至少包含 `source_plugin_id`、`source_type`、`title`、`url`、正文文本相关字段、`raw_payload` 和必要 `metadata`
- **AND** 平台随后负责将该结果写入事件链路、持久化并通过 Event Bus 发布

### Requirement: Jina Reader Plugin Boundary Excludes Runtime And Event Responsibilities

`Jina Reader` 插件 MUST NOT 承担平台运行时和事件链路职责。

#### Scenario: Plugin capability remains limited to read and normalize

- **GIVEN** 插件被实现为官方 Source Plugin
- **WHEN** 审查插件边界
- **THEN** 插件 MUST 只负责通过外部 reader 服务读取内容、标准化和清晰失败返回
- **AND** 插件 MUST NOT 负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限检查或生命周期托管

### Requirement: Jina Reader Plugin Follows Platform Outbound Policy

`Jina Reader` 插件 MUST 遵循平台传入的允许/禁止外发策略或等价 policy 结果，不自行承担 URL 是否可外发的最终判定职责。

#### Scenario: Platform marks a URL as not allowed for outbound reader access

- **GIVEN** 平台向插件传入一个被判定为不允许外发的 URL 或等价策略结果
- **WHEN** 插件评估是否调用外部 reader 服务
- **THEN** 插件 MUST NOT 将该 URL 发送给外部 reader
- **AND** 插件 MUST 返回清晰拒绝或失败信息

### Requirement: External Reader Failures Return Clear Errors Without Automatic Fallback

`Jina Reader` 插件在外部 reader 限流、超时、不可用或返回失败时 MUST 返回清晰失败信息，而不是自动切换到其他 reader。

#### Scenario: External reader service fails or is unavailable

- **GIVEN** 插件需要访问外部 reader 服务
- **WHEN** 外部 reader 出现限流、超时、服务不可用或返回失败
- **THEN** 插件 MUST 返回清晰失败信息
- **AND** 插件 MUST NOT 在本轮实现中自动切换到 `Readability` 或其他 reader 路径
