## ADDED Requirements

### Requirement: QuantAgent MUST expose a real Discord interactions HTTP endpoint

QuantAgent SHALL 提供一个可配置给 Discord Developer Portal 的真实 HTTP endpoint，用于接收 Discord interaction webhook 请求。

#### Scenario: Discord can reach a stable POST endpoint
- **WHEN** 运维或开发者在 Discord Developer Portal 中配置 Interactions Endpoint URL
- **THEN** QuantAgent 提供一个稳定的 `POST` HTTP endpoint 可用于接收 Discord interaction 请求
- **AND** 该 endpoint 由 `apps/api` 管理，而不是由插件目录自行启动独立服务

### Requirement: The endpoint MUST validate official Discord request signatures

真实 Discord interaction endpoint SHALL 使用 Discord 官方请求头和 `Ed25519` 校验每个入站请求。

#### Scenario: Invalid signature is rejected
- **WHEN** endpoint 收到缺失或非法的 `X-Signature-Ed25519` 或 `X-Signature-Timestamp` 请求
- **THEN** 系统拒绝该请求
- **AND** 返回 `401` 或等价未授权结果

#### Scenario: Valid signature passes verification
- **WHEN** endpoint 收到带有合法 `X-Signature-Ed25519`、合法 `X-Signature-Timestamp` 和原始 body 的请求
- **THEN** 系统使用 Discord application public key 完成 `Ed25519` 校验
- **AND** 只有校验通过后才进入后续 payload 解析

### Requirement: The endpoint MUST support Discord PING verification

真实 Discord interaction endpoint SHALL 支持 Discord Developer Portal 的 `PING` 验证握手。

#### Scenario: PING request returns PONG
- **WHEN** endpoint 收到一个通过签名校验且 payload `type` 为 `1` 的 Discord interaction 请求
- **THEN** 系统返回 `200` 响应
- **AND** 响应 body 为合法的 Discord `PONG` interaction response

### Requirement: Application commands MUST produce a valid initial interaction response

对于首版支持的 Discord application command interaction，系统 SHALL 在 Discord 限时窗口内返回合法首响，而不是只做本地解析。

#### Scenario: Supported application command receives immediate response
- **WHEN** endpoint 收到一个通过签名校验且 payload `type` 为 `2` 的合法 interaction 请求
- **THEN** 系统返回 `200` 和合法的 Discord interaction response
- **AND** 该响应不依赖后续 followup message 基础设施才算成功

#### Scenario: Unsupported interaction type is handled explicitly
- **WHEN** endpoint 收到一个通过签名校验但当前版本不支持的 interaction type
- **THEN** 系统返回明确的不支持结果
- **AND** 不会伪装成成功处理

### Requirement: API ingress MUST invoke the single Discord plugin via manifest entrypoint

真实 Discord interaction ingress SHALL 通过 Registry record 和 `plugin.yaml` 中的 `entrypoint` 定位单个官方 Discord 插件，而不是在核心代码里硬编码 Discord 插件 import。

#### Scenario: API resolves the configured Discord plugin from Registry
- **WHEN** endpoint 需要处理一条 Discord interaction 请求
- **THEN** API 层根据已配置的 plugin id 在 Registry 中定位一个合法的 Discord plugin record
- **AND** 通过该 record 的 manifest entrypoint 加载插件对象

#### Scenario: API validates receive capability without relying on source type
- **WHEN** endpoint 校验目标 Discord 插件是否合法可接收请求
- **THEN** 它校验 manifest capability 集合与 `receive_request` handler
- **AND** 它不再把 `type == source` 作为唯一前置条件

#### Scenario: Missing or invalid plugin configuration fails safely
- **WHEN** endpoint 配置的 plugin id 不存在、记录非法或 entrypoint 无法加载
- **THEN** 系统返回结构化失败结果
- **AND** 错误结果不暴露本地路径、secret 原文或内部 traceback

### Requirement: The Discord plugin MUST support official interaction verification and parsing

Discord 官方插件 SHALL 支持 Discord 官方 interaction 请求的验签、最小解析和插件内 DTO 产出。

#### Scenario: Valid application command produces a plugin DTO
- **WHEN** Discord 插件收到一条通过官方签名校验的合法 application command interaction
- **THEN** 插件产出标准化 DTO
- **AND** DTO 至少包含 interaction 标识、来源标识、文本内容和 payload 摘要

#### Scenario: Plugin no longer depends on HMAC fixture as production behavior
- **WHEN** 真实 Discord interaction 请求进入插件
- **THEN** 插件生产路径使用 Discord 官方 `Ed25519` 校验
- **AND** HMAC fixture 如继续存在也只能作为测试夹具而不是生产协议

### Requirement: Real ingress configuration MUST be externalized and documented

真实 Discord interaction ingress 所需的 endpoint、plugin id、公钥和插件配置 SHALL 通过可审计配置提供，而不能硬编码在源码中。

#### Scenario: Runtime values come from configuration
- **WHEN** 开发者或部署环境启用真实 Discord interaction endpoint
- **THEN** endpoint 启用开关、目标 plugin id 和 Discord public key 值来自环境变量或等价配置入口
- **AND** 这些值不写死在路由代码、测试样例或 README 示例中

#### Scenario: Documentation explains real setup and smoke test
- **WHEN** 开发者阅读相关 README 或运行说明
- **THEN** 文档说明如何配置 Discord Developer Portal endpoint、如何设置本地环境变量以及如何执行真实 smoke test
- **AND** 文档明确哪些能力仍未接入 Event Bus、审批或自动执行链路
