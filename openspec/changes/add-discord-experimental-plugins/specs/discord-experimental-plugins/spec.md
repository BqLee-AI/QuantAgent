## ADDED Requirements

### Requirement: 官方 Discord 实验插件必须沿用现有插件类型边界

QuantAgent SHALL 通过两个官方插件实现第一版 Discord 实验性收发能力：发送使用 `notification` 插件类型，接收使用 `source` 插件类型。

#### Scenario: 发送与接收分别以官方插件注册
- **WHEN** 仓库实现第一版 Discord 官方实验插件组
- **THEN** 至少存在一个 `notification` 类型的 Discord 发送插件
- **AND** 至少存在一个 `source` 类型的 Discord 接收插件
- **AND** 两个插件都通过各自目录内的 `plugin.yaml` 注册进入系统

#### Scenario: 第一版不通过混合插件绕过类型边界
- **WHEN** 实现者为第一版 Discord 能力选择插件组织方式
- **THEN** 发送能力不能通过 `source` 插件顺带承担
- **AND** 接收能力不能通过 `notification` 插件顺带承担
- **AND** 核心代码不能通过硬编码 class、import 列表或 if/else 注册 Discord 插件

#### Scenario: 官方 Discord 插件提供最小目录结构样板
- **WHEN** 开发者查看第一版 Discord 官方实验插件目录
- **THEN** 每个插件目录至少包含 `plugin.yaml`、`config.schema.json`、`README.md` 和最小实现/测试文件
- **AND** 发送插件落在 `plugins/notifications/` 下
- **AND** 接收插件落在 `plugins/sources/` 下

### Requirement: Discord 发送插件提供最小可测发送路径

Discord 发送插件 SHALL 提供最小可独立测试的消息发送能力，并限制在低风险通知边界内。

#### Scenario: 有效配置可发送最小文本消息
- **WHEN** 发送插件收到有效配置和一条最小文本消息
- **THEN** 插件可以向 Discord webhook 或等价 mock endpoint 发起发送请求
- **AND** 该请求不依赖核心 Runtime、审批流或真实交易执行链路

#### Scenario: 发送失败以结构化结果返回
- **WHEN** webhook 配置缺失、上游返回失败、请求超时或网络异常
- **THEN** 发送插件返回结构化失败结果
- **AND** 失败结果包含适合测试和审计的错误摘要
- **AND** 失败结果不暴露 secret 原文、webhook URL 全量值或私有频道信息

### Requirement: Discord 接收插件使用 Webhook Push 最小路径

Discord 接收插件 SHALL 以 `Webhook Push` 作为第一版唯一接收路径，并在插件边界内完成鉴权和最小解析。

#### Scenario: 合法 inbound payload 可被接收
- **WHEN** 接收插件收到合法请求头上下文、有效配置和合法 Discord inbound payload
- **THEN** 插件可以完成鉴权与最小解析
- **AND** 插件返回表示接收成功的结果

#### Scenario: 第一版不要求 polling 或 gateway
- **WHEN** 第一版 Discord 接收能力被实现
- **THEN** 该实现不要求 bot polling
- **AND** 该实现不要求 gateway stream 订阅
- **AND** 这些能力如需支持应由后续 change 单独定义

### Requirement: Discord 接收结果只标准化到插件内 DTO

第一版 Discord 接收插件 SHALL 将成功接收的入站消息标准化为插件内 DTO，而不是直接接入核心事件流。

#### Scenario: 合法消息被解析为插件内 DTO
- **WHEN** 接收插件成功处理一条合法 inbound payload
- **THEN** 输出结果包含插件内标准化 DTO
- **AND** DTO 至少能表达消息标识、来源标识、消息文本和原始 payload 摘要

#### Scenario: 第一版不接入核心系统契约
- **WHEN** 第一版接收能力完成最小解析
- **THEN** 该结果不直接进入 Event Bus
- **AND** 该结果不定义新的系统级 `RawEvent`、统一聊天通道或审批回流契约
- **AND** 如需引入这些核心契约，必须先通过新的 OpenSpec change 审核

### Requirement: Discord 插件配置必须通过 schema 描述且隔离敏感值

两个 Discord 官方插件 SHALL 使用 `config.schema.json` 描述最小配置，并通过 secret reference 表达敏感字段。

#### Scenario: 发送插件配置只暴露最小发送所需字段
- **WHEN** 实现者查看 Discord 发送插件的配置 schema
- **THEN** schema 至少描述 webhook 相关 secret reference 字段
- **AND** schema 不包含真实 webhook URL、token 或私有频道值

#### Scenario: 接收插件配置只暴露最小接收所需字段
- **WHEN** 实现者查看 Discord 接收插件的配置 schema
- **THEN** schema 至少描述签名校验所需 secret/public key reference
- **AND** schema 可以描述最小 allowlist 配置
- **AND** schema 不包含真实 signing secret、token 或私有 guild/channel 信息

### Requirement: Discord 实验插件必须可以独立 mock 验证

第一版 Discord 官方实验插件 SHALL 提供不依赖系统级联调的独立验证路径。

#### Scenario: 发送插件可以通过 mock endpoint 验证
- **WHEN** 开发者运行发送插件的独立测试
- **THEN** 测试可以通过 mock HTTP endpoint 或等价 fixture 验证 payload 构造和成功发送路径
- **AND** 测试可以验证超时与上游失败的结构化错误

#### Scenario: 接收插件可以通过 fixture 验证
- **WHEN** 开发者运行接收插件的独立测试
- **THEN** 测试可以通过 mock inbound payload 和签名/鉴权 fixture 验证接收路径
- **AND** 测试不依赖真实 Discord 环境即可证明“能收、能解析、能报错”

### Requirement: Discord 实验插件必须明确实验边界和非目标

第一版 Discord 官方实验插件 SHALL 在 README 中明确支持范围、非目标和验证方式。

#### Scenario: README 说明支持范围与非目标
- **WHEN** 开发者阅读 Discord 官方实验插件 README
- **THEN** README 清楚说明当前支持发送与 Webhook Push 接收
- **AND** README 清楚说明不支持审批回流、自动执行、主事件流接入、统一聊天通道或完整 Discord 平台集成

#### Scenario: README 不泄露敏感信息
- **WHEN** README 展示配置示例或测试说明
- **THEN** 示例中不出现真实 webhook URL、bot token、signing secret 或私有频道信息
- **AND** README 只描述 secret reference 或占位示例值
