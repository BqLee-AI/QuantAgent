## ADDED Requirements

### Requirement: Plugin Detail V1 exposes a governed detail resource

QuantAgent SHALL expose `GET /api/v1/plugins/{plugin_id}` as a governed plugin detail resource instead of continuing to flatten Registry V1 records.

#### Scenario: 主详情返回命名子域
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins/{plugin_id}`
- **THEN** API 返回标准 `ApiResponse` envelope
- **AND** `data` 包含 `overview`
- **AND** `data` 包含 `config_summary`
- **AND** `data` 包含 `dependency_summary`
- **AND** `data` 包含 `capabilities`
- **AND** `data` 包含 `health_summary`
- **AND** `data` 包含 `audit_summary`
- **AND** `data` 包含 `ops_summary`
- **AND** `data` 包含 `allowed_actions`

#### Scenario: 未知插件返回统一 not found
- **WHEN** 已认证调用方请求不存在的 `plugin_id`
- **THEN** API 返回统一 not-found envelope
- **AND** 不返回伪造的空 detail 对象

#### Scenario: 主详情复用身份字段但不再扁平扩写
- **WHEN** 主详情返回 `overview`
- **THEN** `overview` 复用 Plugin Registry V1 已公开的身份字段
- **AND** config、dependency、health、audit 和 ops 信息不会继续平铺在原始 registry record 同层

### Requirement: Overview stays within identity and governance summary boundaries

Plugin Detail V1 SHALL keep `overview` limited to plugin identity and governance summary data.

#### Scenario: overview 只暴露最小治理摘要
- **WHEN** API 返回 `overview`
- **THEN** `overview` 至少包含 `plugin_id`、`name`、`type`、`version`、`source` 和 `status`
- **AND** `overview` 可以包含 `description`
- **AND** `overview` 可以包含 `blocked_reason_summary`
- **AND** `overview` 可以包含 `last_error_summary`

#### Scenario: overview 不暴露内部实现细节
- **WHEN** API 返回 `overview`
- **THEN** `overview` 不暴露 manifest 原文
- **AND** `overview` 不暴露 entrypoint 细节
- **AND** `overview` 不暴露插件绝对路径
- **AND** `overview` 不暴露未治理的私有 metadata

### Requirement: Config summary and config detail are read-only and masked

Plugin Detail V1 SHALL expose governed config visibility without returning secret-bearing values in plaintext.

#### Scenario: 主详情只返回 config summary
- **WHEN** API 返回 `config_summary`
- **THEN** `config_summary` 至少包含 `config_state`
- **AND** `config_summary` 至少包含 `missing_required_count`
- **AND** `config_summary` 至少包含 `masked_sensitive_count`
- **AND** `config_summary` 可以包含 `schema_version`
- **AND** `config_summary` 可以包含 `last_validated_at`
- **AND** `config_summary` 可以包含 `reload_required`

#### Scenario: config 子资源分层返回 schema 与当前值
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins/{plugin_id}/config`
- **THEN** API 返回标准 `ApiResponse` envelope
- **AND** `data` 以受控方式区分 schema 信息与当前值信息
- **AND** secret-bearing values 只返回 masked value 或 secret reference
- **AND** API 不返回 secret 明文

#### Scenario: 配置尚未接入时有清晰退化语义
- **WHEN** 插件当前没有可读取的配置明细
- **THEN** `config_summary` 或 `/config` 返回 `not_configured`、`unavailable` 或 `forbidden` 等可区分语义
- **AND** 不只返回语义不清的 `null`

### Requirement: Dependencies stay separate from SourceBinding and runtime scheduling objects

Plugin Detail V1 SHALL expose plugin dependency information without collapsing SourceBinding or SchedulerRun into the dependency contract.

#### Scenario: dependency summary 只返回总体状态
- **WHEN** API 返回 `dependency_summary`
- **THEN** `dependency_summary` 至少包含 required 与 optional 的总体数量
- **AND** `dependency_summary` 至少包含 `missing_count`
- **AND** `dependency_summary` 可以包含 `blocked_reason_summary`

#### Scenario: dependencies 子资源返回结构化依赖明细
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins/{plugin_id}/dependencies`
- **THEN** API 返回标准 `ApiResponse` envelope
- **AND** `data` 可以分别表达 plugin、python、system 和 reverse dependency 明细
- **AND** 每条依赖都能区分 required/optional 与 resolved state
- **AND** 每条依赖都可以表达 blocked reason

#### Scenario: SourceBinding 不混入 dependencies
- **WHEN** 插件类型为 industry 或 source
- **THEN** `dependencies` 契约不直接返回 SourceBinding 对象列表
- **AND** 与 SourceBinding 或 SchedulerRun 相关的资源边界由后续专门 change 定义

### Requirement: Capabilities include governance hints and broker safety boundaries

Plugin Detail V1 SHALL expose capabilities as governed declarations rather than unmanaged plugin-specific blobs.

#### Scenario: capabilities 返回最小治理字段
- **WHEN** API 返回 `capabilities`
- **THEN** 每项 capability 至少包含 `name`
- **AND** 每项 capability 至少包含 `risk_level`
- **AND** 每项 capability 可以表达 `requires_policy_gate`
- **AND** 每项 capability 可以表达 `requires_approval`
- **AND** 每项 capability 可以表达 `availability_state`

#### Scenario: broker capability 不暗示真实交易已支持
- **WHEN** 插件类型为 `broker`
- **THEN** capability 或 ops 信息必须明确 V1 只支持 `disabled`、`dry_run` 或 `mock` 边界
- **AND** API 不暗示 live trading 已默认可用

### Requirement: Health stays plugin-centric and distinguishes degraded states

Plugin Detail V1 SHALL expose plugin-centric health summaries without turning the detail endpoint into a runtime-wide diagnostics dump.

#### Scenario: 主详情返回 health summary
- **WHEN** API 返回 `health_summary`
- **THEN** `health_summary` 至少包含 `status`
- **AND** `health_summary` 可以包含 `last_check_at`
- **AND** `health_summary` 可以包含 `last_error_summary`
- **AND** `health_summary` 可以包含 `latest_runtime_failure_ref`

#### Scenario: health 子资源只围绕单插件
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins/{plugin_id}/health`
- **THEN** API 返回该插件的最近健康与失败摘要
- **AND** API 不返回 runtime 全局时间线
- **AND** API 不替代后续 runtime inspect 资源

#### Scenario: 健康退化语义可区分
- **WHEN** 健康数据未采集、暂不可用、权限受限或已经降级
- **THEN** 契约能区分 `not_collected`
- **AND** 契约能区分 `unavailable`
- **AND** 契约能区分 `forbidden`
- **AND** 契约能区分 `degraded`

### Requirement: Audit stays append-only and sanitized

Plugin Detail V1 SHALL expose plugin-centric audit summaries and recent records without leaking sensitive payloads.

#### Scenario: 主详情返回 audit summary
- **WHEN** API 返回 `audit_summary`
- **THEN** `audit_summary` 可以包含 `last_changed_at`
- **AND** `audit_summary` 可以包含 `last_actor`
- **AND** `audit_summary` 可以包含最近 action 类型摘要
- **AND** `audit_summary` 可以包含最近 audit 引用

#### Scenario: audit 子资源返回最近受控记录
- **WHEN** 已认证调用方请求 `GET /api/v1/plugins/{plugin_id}/audit`
- **THEN** API 返回最近 N 条插件审计记录的标准 envelope
- **AND** 每条记录可以包含 actor、action、result 和 occurred_at
- **AND** 审计记录保持 append-only 语义

#### Scenario: 审计不泄露敏感字段
- **WHEN** 审计记录涉及配置、secret reference 或内部错误
- **THEN** API 不返回 secret 明文
- **AND** API 不返回原始敏感 payload
- **AND** API 不返回内部 stack trace 或本地私有路径

### Requirement: Ops summary and allowed actions are hints, not implicit mutations

Plugin Detail V1 SHALL expose action hints and blockers without pretending that all plugin operations are already implemented.

#### Scenario: 主详情返回可展示动作提示
- **WHEN** API 返回 `ops_summary` 与 `allowed_actions`
- **THEN** `ops_summary` 可以表达 `operable_state`
- **AND** `ops_summary` 可以表达 action blockers
- **AND** `allowed_actions` 中每项都能表达 `action`
- **AND** `allowed_actions` 中每项都能表达 `allowed`
- **AND** `allowed_actions` 中每项都能表达 `disabled_reason`

#### Scenario: action hint 不等于动作已实现
- **WHEN** 主详情返回某个 `allowed_actions` 项
- **THEN** 该字段只表示展示与后续导航提示
- **AND** 该字段不自动表示对应 mutation 已在当前版本实现

#### Scenario: future mutations 统一挂在 actions 路径
- **WHEN** 后续 change 落地插件写操作
- **THEN** 写操作应挂在 `/api/v1/plugins/{plugin_id}/actions/*`
- **AND** Plugin Detail V1 不在本 change 内要求实现这些 mutation

### Requirement: Plugin detail responses remain sanitized and minimally visible under permission constraints

Plugin Detail V1 SHALL keep responses sanitized and support permission-aware partial visibility.

#### Scenario: 权限受限时仍可返回最小可见概览
- **WHEN** 调用方有权查看插件存在性但无权查看完整详情子域
- **THEN** API 可以继续返回最小 `overview`
- **AND** 受限子域以 `forbidden` 或受控裁剪结果表达
- **AND** API 不因单个子域受限而泄露敏感内容

#### Scenario: 错误摘要保持脱敏
- **WHEN** 主详情或子资源返回 `last_error_summary`
- **THEN** 错误摘要只包含适合 API 返回的结构化 code、message、stage 和安全 details
- **AND** 错误摘要不暴露 secret、token、cookie、stack trace 或本地私有路径
