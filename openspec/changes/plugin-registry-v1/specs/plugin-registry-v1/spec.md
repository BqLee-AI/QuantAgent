## ADDED Requirements

### Requirement: 插件 manifest 是 Registry 真源

QuantAgent SHALL 使用 `plugin.yaml` 作为 Plugin Registry V1 对官方插件和运行时插件的登记真源。

#### Scenario: 扫描官方与运行时插件目录
- **WHEN** Registry 扫描插件
- **THEN** Registry 读取 `plugins/**/plugin.yaml` 中的插件 manifest
- **AND** 当运行时目录存在时，Registry 读取 `runtime/plugins/**/plugin.yaml` 中的插件 manifest
- **AND** 缺失的 `runtime/plugins` 目录被视为空插件来源

#### Scenario: 忽略没有 manifest 的目录
- **WHEN** Registry 在插件根目录下遇到不包含 `plugin.yaml` 的目录
- **THEN** 这些目录被忽略
- **AND** 这些目录不会生成失败的插件记录

#### Scenario: V1 中 entrypoint 只是元数据
- **WHEN** manifest 声明 `entrypoint`
- **THEN** Registry 只校验该字段存在且非空
- **AND** Registry 在 V1 中不会 import、实例化或执行该 entrypoint

### Requirement: 插件 manifest 校验是结构化的

Registry SHALL 将插件 manifest 校验为结构化记录，并保证单个非法插件不会破坏完整扫描。

#### Scenario: 合法 placeholder 插件可被发现
- **WHEN** Registry 扫描 `plugins/sources/placeholder-source/plugin.yaml`
- **THEN** Registry 返回 id 为 `quantagent.official.source.placeholder` 的插件记录
- **AND** 该记录包含 type、version、capabilities、config schema 路径、source、path 和 status

#### Scenario: 必填 manifest 字段会被强制校验
- **WHEN** manifest 缺少 `id`、`name`、`type`、`version`、`entrypoint`、`capabilities` 或 `config_schema` 中任一字段
- **THEN** 对应插件记录被标记为 `invalid`
- **AND** `last_error` 说明缺失或非法字段

#### Scenario: 配置 schema 文件必须存在
- **WHEN** manifest 引用 `config_schema`
- **THEN** 被引用的 JSON Schema 文件必须存在于插件目录下
- **AND** schema 文件缺失会让插件记录被标记为 `invalid`
- **AND** 完整扫描会继续处理其他插件

#### Scenario: 未知插件类型会被拒绝
- **WHEN** manifest 声明的 type 不在 V1 支持集合内
- **THEN** 该插件记录被标记为 `invalid`
- **AND** `last_error` 包含结构化的未知类型摘要

### Requirement: 插件类型使用 canonical broker 命名

Registry SHALL 使用 canonical 插件类型命名，并为历史 `executor` / `trade_executor` manifest 保留兼容路径。

#### Scenario: executor alias 会被归一化
- **WHEN** manifest 声明 `type: executor` 或 `type: trade_executor`
- **THEN** Registry 可以将其作为兼容别名接受
- **AND** Registry 对外暴露的 canonical type 是 `broker`
- **AND** 该兼容行为不会启用真实交易执行

#### Scenario: V1 支持类型是显式集合
- **WHEN** Registry 校验插件 type
- **THEN** 支持的 canonical type 是 `source`、`industry`、`strategy`、`notification` 和 `broker`
- **AND** 不支持的类型会被报告为 invalid

### Requirement: Registry 扫描失败只影响局部插件

Registry SHALL 将插件扫描失败限制在受影响的插件记录内。

#### Scenario: YAML 格式错误不会中断完整扫描
- **WHEN** 某个插件 manifest 无法按 YAML 解析
- **THEN** 该插件结果表示为 `invalid` 或 `failed`
- **AND** 其他合法插件仍然会被返回

#### Scenario: 重复插件 id 会被报告
- **WHEN** 两个 manifest 声明相同插件 id
- **THEN** Registry 在受影响的插件记录中标记冲突
- **AND** V1 不尝试依赖求解或版本选择

#### Scenario: 错误信息适合 API 响应
- **WHEN** 插件记录包含 `last_error`
- **THEN** 错误信息包含适合 API 响应的结构化 code、message、stage 和 details
- **AND** 错误信息不暴露 secret、stack trace 或本地环境值

### Requirement: 存在最小插件状态模型

Registry SHALL 暴露最小 V1 状态模型，用于表达发现和管理状态，但不暗示插件代码已经执行。

#### Scenario: V1 状态值有明确边界
- **WHEN** Registry 返回插件记录
- **THEN** 插件 status 是 `discovered`、`valid`、`invalid`、`enabled`、`disabled` 或 `failed` 之一

#### Scenario: enabled 不等于 loaded
- **WHEN** V1 中插件被标记为 `enabled`
- **THEN** 该状态只代表管理配置状态
- **AND** 该状态不表示插件 entrypoint 已经被 import
- **AND** 该状态不表示 `load`、`start`、scheduler subscription 或 tool registration 已经发生

### Requirement: 插件管理 API 是薄边界

API SHALL 暴露最小受保护插件管理面，并由 core Registry 提供数据。

#### Scenario: 插件列表 endpoint 返回 envelope
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins`
- **THEN** API 返回标准 `ApiResponse` envelope
- **AND** data 包含 core Registry 产生的插件记录

#### Scenario: 插件详情 endpoint 返回单条记录
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins/{plugin_id}`
- **THEN** API 在标准 envelope 中返回匹配插件记录
- **AND** 未知 plugin id 返回现有 not found envelope 形态

#### Scenario: 配置 schema endpoint 返回 manifest schema
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins/{plugin_id}/config-schema`
- **THEN** API 返回 manifest 引用的插件配置 JSON Schema
- **AND** route 不 import 或实例化插件 entrypoint

#### Scenario: rescan endpoint 刷新 registry 视图
- **WHEN** 已认证调用方请求 `POST /api/v1/plugins/actions/rescan`
- **THEN** API 调用 Registry scanner
- **AND** 响应包含 scan summary 和标准 envelope
- **AND** route 不安装依赖、不热重载插件代码、不执行插件 hook

### Requirement: Plugin Registry V1 推迟运行时执行

Plugin Registry V1 SHALL 将运行时执行、依赖安装和高风险动作能力推迟到后续 change。

#### Scenario: 不自动安装依赖
- **WHEN** manifest 声明 plugin、Python 或 system dependencies
- **THEN** V1 可以保留这些元数据
- **AND** V1 不自动安装缺失依赖

#### Scenario: 不发生真实交易执行
- **WHEN** 插件声明 `broker` capabilities
- **THEN** V1 只把这些 capabilities 视为元数据
- **AND** V1 不暴露真实下单、broker adapter 调用或 live trading actions

#### Scenario: Source 样板推迟到 V1.1
- **WHEN** 本 OpenSpec 被批准后开始实现
- **THEN** 初始实现聚焦 Registry、API 和诊断能力
- **AND** pull source 样板和 RawEvent 产出链路由后续 change 或后续实现阶段处理

### Requirement: 插件协议归 QuantAgent 管理

QuantAgent SHALL 统一管理插件 manifest、配置、生命周期、能力暴露、错误结构和高风险动作协议。

#### Scenario: 插件不能私自定义协议入口
- **WHEN** 插件希望进入 QuantAgent 系统
- **THEN** 插件必须通过 `plugin.yaml` 和 Registry 登记
- **AND** 插件不能依赖核心代码中的硬编码 class、import 列表或 if/else 注册

#### Scenario: 配置协议由 schema 管理
- **WHEN** 插件需要配置
- **THEN** 插件必须通过 manifest 引用的 `config.schema.json` 描述配置形态
- **AND** 插件不能要求 API、前端或 worker 直接理解插件私有配置格式

#### Scenario: 后续 tool/action 暴露必须经过治理边界
- **WHEN** 插件后续暴露 tool、action、source binding 或 broker 能力
- **THEN** 这些能力必须进入 ToolRegistry、capability、risk level、Policy Gate 或 audit 等宿主治理边界
- **AND** 插件不能绕过这些边界直接执行高风险动作

### Requirement: Registry V1 指向完整插件流程

Registry V1 SHALL 被定义为完整插件体系的第一阶段，而不是最终插件平台。

#### Scenario: 完整流程有阶段顺序
- **WHEN** 后续实现者扩展插件体系
- **THEN** 实现顺序应从 manifest 发现、manifest/config 校验、Registry 状态、enable/disable 管理开始
- **AND** 再逐步进入 RuntimeContext、生命周期、ToolRegistry 或 Scheduler 调用
- **AND** 最后才进入 Decision、Policy Gate、dry-run、notification、audit 或其他高风险动作链路

#### Scenario: V1 不阻断后续协议演进
- **WHEN** 后续 change 增加生命周期、工具注册或 source 调度
- **THEN** 它们应复用 V1 的 plugin id、manifest、config schema、status 和 error 结构
- **AND** 不应另建一套绕过 Registry 的插件发现或配置协议

### Requirement: 后续最小插件 demo 是验收资产

后续 V1.1 change SHALL 提供一个最小官方插件 demo，用于证明插件作者如何按 QuantAgent 协议接入系统。

#### Scenario: demo 插件展示最小文件结构
- **WHEN** V1.1 实现 demo 插件
- **THEN** demo 插件包含 `plugin.yaml` 和 `config.schema.json`
- **AND** demo 插件可以展示最小 Python entrypoint 结构
- **AND** demo 插件不依赖核心硬编码注册

#### Scenario: demo 插件只走低风险路径
- **WHEN** demo 插件被用于验证插件系统
- **THEN** demo 插件优先采用 `source` 类型
- **AND** demo 插件只产生只读、mock 或 RawEvent 样例输出
- **AND** demo 插件不接真实交易、真实外部副作用或自动依赖安装
