## ADDED Requirements

### Requirement: 官方 Discord 实验能力必须以单个官方插件注册

QuantAgent SHALL 通过一个官方 Discord 插件实现第一版实验性收发能力，而不是通过两个独立官方插件分别承接发送和接收。

#### Scenario: 单个官方 Discord 插件进入系统
- **WHEN** 仓库实现第一版 Discord 官方实验能力
- **THEN** 至少存在一个官方 Discord 插件通过 `plugin.yaml` 注册进入系统
- **AND** 该插件拥有单个 plugin id、单个 manifest 和单个 config schema

#### Scenario: 第一版不再维持发送/接收双插件拆分
- **WHEN** 实现者为第一版 Discord 能力选择插件组织方式
- **THEN** 发送能力和接收能力都由同一个官方 Discord 插件承接
- **AND** 核心代码不能通过硬编码 class、import 列表或 if/else 注册 Discord 插件

#### Scenario: 官方 Discord 插件提供统一目录样板
- **WHEN** 开发者查看第一版 Discord 官方实验插件目录
- **THEN** 该目录至少包含 `plugin.yaml`、`config.schema.json`、`README.md` 和最小实现/测试文件
- **AND** 发送与接收的 smoke/test 入口在同一官方插件目录下可定位

### Requirement: Discord 单插件提供最小可测发送路径

Discord 单插件 SHALL 提供最小可独立测试的消息发送能力，并限制在低风险通知边界内。

#### Scenario: 有效配置可发送最小文本消息
- **WHEN** Discord 插件收到有效配置和一条最小文本消息
- **THEN** 插件可以向 Discord webhook 或等价 mock endpoint 发起发送请求
- **AND** 该请求不依赖核心 Runtime、审批流或真实交易执行链路

#### Scenario: 发送失败以结构化结果返回
- **WHEN** webhook 配置缺失、上游返回失败、请求超时或网络异常
- **THEN** Discord 插件返回结构化失败结果
- **AND** 失败结果包含适合测试和审计的错误摘要
- **AND** 失败结果不暴露 secret 原文、webhook URL 全量值或私有频道信息

### Requirement: Discord 单插件提供 Webhook Push 最小接收路径

Discord 单插件 SHALL 在同一插件边界内提供 `Webhook Push` 接收能力，并完成鉴权和最小解析。

#### Scenario: 合法 inbound payload 可被接收
- **WHEN** Discord 插件收到合法请求头上下文、有效配置和合法 Discord inbound payload
- **THEN** 插件可以完成鉴权与最小解析
- **AND** 插件返回表示接收成功的结果

#### Scenario: 第一版不要求 polling 或 gateway
- **WHEN** 第一版 Discord 接收能力被实现
- **THEN** 该实现不要求 bot polling
- **AND** 该实现不要求 gateway stream 订阅
- **AND** 这些能力如需支持应由后续 change 单独定义

### Requirement: Discord 接收结果只标准化到插件内 DTO

第一版 Discord 单插件 SHALL 将成功接收的入站消息标准化为插件内 DTO，而不是直接接入核心事件流。

#### Scenario: 合法消息被解析为插件内 DTO
- **WHEN** Discord 插件成功处理一条合法 inbound payload
- **THEN** 输出结果包含插件内标准化 DTO
- **AND** DTO 至少能表达消息标识、来源标识、消息文本和原始 payload 摘要

#### Scenario: 第一版不接入核心系统契约
- **WHEN** 第一版接收能力完成最小解析
- **THEN** 该结果不直接进入 Event Bus
- **AND** 该结果不定义新的系统级 `RawEvent`、统一聊天通道或审批回流契约
- **AND** 如需引入这些核心契约，必须先通过新的 OpenSpec change 审核

### Requirement: Discord 单插件配置必须通过统一 schema 描述且隔离敏感值

第一版 Discord 官方实验插件 SHALL 使用单个 `config.schema.json` 描述最小配置，并通过 secret reference 表达敏感字段。

#### Scenario: 统一 schema 暴露发送与接收所需最小字段
- **WHEN** 实现者查看 Discord 插件的配置 schema
- **THEN** schema 至少描述 webhook 相关 secret reference 字段
- **AND** schema 至少描述签名校验所需 public key 或 reference 字段
- **AND** schema 可以描述最小 allowlist 与响应文本配置

#### Scenario: 统一 schema 不暴露敏感值
- **WHEN** 实现者查看 Discord 插件的配置 schema
- **THEN** schema 不包含真实 webhook URL、token、私钥或私有 guild/channel 值

### Requirement: Discord 实验插件必须可以独立 mock 验证

第一版 Discord 官方实验插件 SHALL 提供不依赖系统级联调的独立验证路径。

#### Scenario: 发送能力可以通过 mock endpoint 验证
- **WHEN** 开发者运行 Discord 插件的发送测试
- **THEN** 测试可以通过 mock HTTP endpoint 或等价 fixture 验证 payload 构造和成功发送路径
- **AND** 测试可以验证超时与上游失败的结构化错误

#### Scenario: 接收能力可以通过 fixture 验证
- **WHEN** 开发者运行 Discord 插件的接收测试
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
