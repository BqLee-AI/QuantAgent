## ADDED Requirements

### Requirement: Official Twelve Data Quote Plugin Package

系统 MUST 支持一个官方 `Twelve Data` latest quote Source Plugin，作为 `plugins/sources/` 下可分发的插件包交付。

#### Scenario: Official plugin package is defined with minimum deliverables

- **GIVEN** 仓库需要新增官方股价 / 行情 source 能力
- **WHEN** 实现者按本 change 落地首个 `Twelve Data` quote 插件包
- **THEN** 插件包 MUST 包含 `plugin.yaml`、`config.schema.json`、README、入口实现和最小测试
- **AND** 插件 MUST 通过 `plugin.yaml` 注册为 `source` 类型官方插件
- **AND** `plugin.yaml` MUST 声明插件 ID 为 `quantagent.official.source.twelve_data`
- **AND** `plugin.yaml` MUST 声明 `execution_mode: pull`
- **AND** `plugin.yaml` MUST 声明 `source.fetch` capability

### Requirement: Twelve Data Quote Plugin Consumes Platform-Validated Config

`Twelve Data` quote 插件 MUST 只消费平台传入的校验后配置 DTO / `effective_config`，不负责配置保存或运行时编排。

#### Scenario: Plugin receives symbols and minimal request configuration from platform

- **GIVEN** 用户通过控制台或 API 提交了插件配置
- **AND** 平台已经完成 schema 校验和绑定
- **WHEN** 平台调用 `Twelve Data` quote 插件
- **THEN** 插件 MUST 读取非空 `symbols`
- **AND** 插件 MAY 读取可选 `market`、`timeout_seconds` 和等价的最小非敏感控制字段
- **AND** 插件 MUST NOT 在公开 `config.schema.json` 中直接提交真实 Twelve Data API key 值
- **AND** 插件 MUST NOT 自行承担配置保存、启停、调度、审计或生命周期管理

### Requirement: Twelve Data Quote Plugin Returns Platform-Defined Source Output

`Twelve Data` quote 插件 MUST 返回平台约定的 Source Plugin 输出结构 / source runtime 可消费 DTO，而不是引入新的平台级 quote 专用 DTO 或在本 change 中绑定某个 core 内部 DTO 名称。

#### Scenario: Plugin fetches latest quote data for configured symbols

- **GIVEN** 插件收到了有效的 symbol 配置
- **WHEN** 插件通过 Twelve Data latest quote / price 类接口完成拉取和标准化
- **THEN** 插件 MUST 返回平台约定的 Source Plugin 输出结构
- **AND** 返回结果 MUST 对齐 source runtime 可消费的统一输出契约
- **AND** 每条结果 MUST 声明 `source_plugin_id`
- **AND** 每条结果 MUST 声明 `source_type=market_quote`
- **AND** 每条结果 MUST 包含 `raw_payload` 和必要 `metadata`
- **AND** `metadata` MUST 包含 `provider`、`symbol`、`price` 和 `quote_timestamp`

### Requirement: Twelve Data Quote Plugin Defines Stable First-Version Quote Identity

`Twelve Data` quote 插件 MUST 为首版 latest quote 输出定义稳定的最小事件标识来源。

#### Scenario: Plugin normalizes a provider quote into source output

- **GIVEN** 插件已获取某个 symbol 的 latest quote 数据
- **WHEN** 插件将结果转换为平台约定的 Source Plugin 输出结构
- **THEN** 插件 MUST 尝试为该结果构造 `external_id`
- **AND** 首版 `external_id` MUST 采用 `provider:symbol:quote_timestamp` 形状
- **AND** 当 provider 时间字段缺失或格式异常时，插件 MUST 返回清晰失败

### Requirement: Twelve Data Quote Plugin Boundary Excludes Runtime And Market Infrastructure Responsibilities

`Twelve Data` quote 插件 MUST NOT 承担平台运行时和更高层行情基础设施职责。

#### Scenario: Plugin capability remains limited to fetch and normalize latest quotes

- **GIVEN** 插件被实现为官方 Source Plugin
- **WHEN** 审查插件边界
- **THEN** 插件 MUST 只负责调用 Twelve Data、标准化 latest quote 响应和清晰失败返回
- **AND** 插件 MUST NOT 负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限检查或生命周期托管
- **AND** 插件 MUST NOT 在本轮实现中扩展为 WebSocket 行情流、历史序列抓取、新闻抓取或多 provider 聚合器

### Requirement: Twelve Data Quote Plugin Follows Platform Scheduling And Secret Boundaries

`Twelve Data` quote 插件 MUST 遵循平台传入的调度和 secret 边界，不自行实现轮询 runtime 或提交敏感配置。

#### Scenario: Platform controls polling frequency and credentials

- **GIVEN** Twelve Data credits 同时受分钟和每日额度约束
- **WHEN** 插件作为 `pull source` 被接入平台调度
- **THEN** 插件 MUST NOT 自行启动 while loop、后台线程或其他自调度机制
- **AND** 插件 MUST 将轮询频率控制留给平台 scheduler / binding policy
- **AND** 插件 MUST NOT 将真实 API key、生产账户或私有配置作为仓库内公开交付物提交

### Requirement: Twelve Data Failures Return Clear Errors Without Provider Fallback

`Twelve Data` quote 插件在 provider 限流、超时、不可用或响应异常时 MUST 返回清晰失败信息，而不是自动切换到其他 provider。

#### Scenario: Provider request fails or returns unusable quote data

- **GIVEN** 插件需要访问 Twelve Data
- **WHEN** Twelve Data 出现限流、超时、服务不可用、响应缺字段或其他不可用结果
- **THEN** 插件 MUST 返回清晰失败信息
- **AND** 插件 MUST NOT 在本轮实现中自动切换到其他行情 provider
