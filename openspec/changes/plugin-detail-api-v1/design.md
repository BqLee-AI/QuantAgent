## 背景

`plugin-registry-v1` 已经定义了插件发现、最小查询和 `GET /api/v1/plugins/{plugin_id}` 的基础存在性，但那个 detail 仍然是 Registry 视角的最小单条记录，不足以承载插件治理页。`docs/prd/pages/11-plugin-detail.md` 则明确要求插件详情页能解释：

- 插件当前是否可用，以及为什么不可用。
- 配置、依赖、能力、健康、审计和运维动作入口各自属于哪个子域。
- 对于 broker、industry、source 等不同类型插件，哪些信息可以稳定展示，哪些需要后续 issue 单独定义。

本 change 的设计目标是定义一个“插件为中心”的只读详情契约，同时避免把 runtime inspect、SourceBinding 或 future 写动作过早混入。

## 目标与非目标

**目标：**

- 定义插件详情主资源与子资源边界。
- 定义七个子域的字段所有权、脱敏规则和退化语义。
- 明确 `allowed_actions` 与 future `actions/*` 的衔接方式，但不定义写操作实现。
- 明确 API/router、service/read model、Registry/runtime/audit 数据源的职责分工。

**非目标：**

- 不定义配置保存、启停、重载、卸载或安装流程。
- 不定义 SourceBinding、SchedulerRun、全局 runtime inspect timeline 的完整契约。
- 不把配置 schema 编辑器、插件日志面板或 marketplace 混进本 change。

## 决策

### 1. 主详情响应承接轻量 summary，重对象走子资源

Plugin Detail V1 采用“主详情 + 子资源”的结构，而不是单个巨型 DTO。

主资源：

- `GET /api/v1/plugins/{plugin_id}`

受控子资源：

- `GET /api/v1/plugins/{plugin_id}/config`
- `GET /api/v1/plugins/{plugin_id}/dependencies`
- `GET /api/v1/plugins/{plugin_id}/health`
- `GET /api/v1/plugins/{plugin_id}/audit`

不单独拆 `capabilities` 和 `ops` 子资源的原因：

- `capabilities` 在 V1 中是相对稳定且轻量的声明信息，适合直接跟随主详情返回。
- `ops` 在 V1 只需要表达“允许什么动作、为什么不允许”，不需要再创建新的 read endpoint。

### 2. 主详情必须复用插件身份字段，但不能继续扁平扩写 Registry DTO

主详情中的 `overview` 复用 Registry V1 已公开的插件身份字段，例如：

- `plugin_id`
- `name`
- `type`
- `version`
- `source`
- `status`

但 Plugin Detail V1 不允许继续把 `config`、`dependencies`、`health`、`audit`、`ops` 直接平铺在原始 `PluginRecord` 同层。主响应必须显式分组为命名子对象，避免前端继续依赖扁平字段推导页面语义。

### 3. 七个子域各自有明确真源和字段边界

建议主详情结构：

```text
PluginDetailResponse
  overview
  config_summary
  dependency_summary
  capabilities
  health_summary
  audit_summary
  ops_summary
  allowed_actions
  links
```

子域边界如下：

#### Overview

只承接插件身份与最小治理摘要：

- `plugin_id`
- `name`
- `type`
- `version`
- `source`
- `status`
- `description`
- `namespace`
- `blocked_reason_summary`
- `last_error_summary`

不承接完整 manifest、entrypoint、绝对路径、依赖明细或审计明细。

#### Config Summary / Config Resource

主详情中的 `config_summary` 只返回：

- `schema_version`
- `config_state`，例如 `valid`、`invalid`、`missing_required`、`not_configured`
- `missing_required_count`
- `masked_sensitive_count`
- `last_validated_at`
- `last_updated_at`
- `reload_required`

`GET /config` 可返回更完整的只读配置视图，但仍必须满足：

- secret-bearing values 只返回 masked value 或 secret reference。
- 不返回 secret 明文。
- 不返回插件私有配置文件路径。
- schema 与当前值分层返回，避免前端把 schema 和 value 混成一个平面对象。

#### Dependency Summary / Dependencies Resource

`dependency_summary` 只表达数量、总体状态和最关键阻塞原因：

- `required_count`
- `optional_count`
- `missing_count`
- `blocked_reason_summary`
- `reverse_dependency_count`

`GET /dependencies` 返回受控依赖明细，允许包含：

- `plugins`
- `python`
- `system`
- `reverse_dependencies`

每条依赖都要明确 `required/optional`、`resolved_state`、`blocked_reason`。

`dependencies` 不得偷带 `SourceBinding` 对象；Industry 与 Source 的绑定关系由后续 #220 / #226 单独定义。

#### Capabilities

主详情直接返回能力声明列表，每项至少表达：

- `name`
- `kind`
- `risk_level`
- `requires_policy_gate`
- `requires_approval`
- `availability_state`

对 broker 类型插件，能力展示必须明确 V1 只支持 `disabled / dry_run / mock` 语义，不暗示真实交易执行已经可用。

#### Health Summary / Health Resource

`health_summary` 只表达插件为中心的最近健康状态：

- `status`，例如 `healthy`、`degraded`、`failed`、`not_collected`、`unavailable`
- `last_check_at`
- `last_error_summary`
- `latest_runtime_failure_ref`

`GET /health` 可以补充最近检查结果和结构化失败摘要，但仍然只围绕单插件。它不是 runtime 全局错误时间线，也不替代 `runtime inspect` 资源。

#### Audit Summary / Audit Resource

`audit_summary` 只表达最近治理活动摘要：

- `last_changed_at`
- `last_actor`
- `recent_action_types`
- `latest_audit_ref`

`GET /audit` 返回最近 N 条插件审计记录的受控视图。记录必须 append-only，可包含 actor、action、result、occurred_at、target_version/config_snapshot_ref，但不得暴露 secret 明文或完整敏感 payload。

#### Ops Summary / allowed_actions

`ops_summary` 只解释插件当前的可操作性状态，例如：

- `operable_state`
- `action_blockers`
- `requires_confirmation`

`allowed_actions` 列出当前可展示的动作 hint，例如 `enable`、`disable`、`reload`、`rescan`。每项至少表达：

- `action`
- `allowed`
- `disabled_reason`
- `requires_confirmation`

V1 中这些字段只作为前端展示和导航提示，不等于动作已经实现。

### 4. 明确定义 unavailable / not_collected / forbidden 语义

本 change 要求 summary 和子资源不能仅靠 `null` 表示退化状态。至少需要这些可区分语义：

- `not_collected`: 系统尚未采集该子域数据。
- `unavailable`: 该插件类型或当前运行模式暂不提供此子域。
- `forbidden`: 调用方无权查看该子域完整信息。
- `degraded`: 已采集到异常或部分失败。

这样前端可以区分“没有数据”“当前无权限”“该能力还未接入”“健康已降级”。

### 5. API 层保持薄，summary 由 core/runtime/audit read model 提供

后续实现目录蓝图建议：

```text
apps/api/src/quantagent/api/
  routers/v1/plugins/
    detail.py
  schemas/plugins/
    detail.py
  services/plugins/
    detail_service.py

packages/core/src/quantagent/core/
  registry/
  runtime/
  audit/
  services/plugin_detail/
```

职责约束：

- router 只做 path 参数、DTO、权限、envelope 和错误映射。
- API DTO 只定义公开契约，不直接复用 ORM model 或内部 read model。
- plugin detail service 负责编排 Registry、runtime health、audit summary 和 capability policy summary。
- Registry/runtime/audit 的内部对象不能直接作为 API response。

### 6. 与其他 issue / change 的职责边界必须显式保留

与 #117：

- `#117` 收 `/plugins` 列表与入口语义。
- 本 change 收 `/plugins/{plugin_id}` 契约，不回退成列表侧栏私有协议。

与 #219：

- `#219` 收前端 Plugin Detail 页面骨架。
- 本 change 提供后端 detail 契约真源。

与 #220 / #226：

- SourceBinding、SchedulerRun 只允许在本 change 中通过 summary ref 或 future link 被提及。
- 它们的对象字段、列表和动作契约不在本 change 定义。

与 `plugin-registry-v1`：

- Registry V1 继续作为身份字段和 manifest 真源。
- Plugin Detail V1 在其之上定义治理型详情 read contract，而不是替换 Registry 的扫描边界。

## 失败路径

- 未找到 plugin id：返回统一 not-found envelope，不返回空详情对象。
- 插件无配置 schema 或未接入配置 read model：`config_summary.config_state` 和 `/config` 需返回清晰 unavailable/not_configured 语义。
- 健康数据未采集：返回 `not_collected`，而不是伪装成 `healthy` 或空值。
- 权限不足：主资源仍可返回基础 `overview`，但受限子域需返回 `forbidden` 语义或受控裁剪结果。
- runtime 错误包含敏感内容：API 只返回脱敏 `last_error_summary`，不返回原始 stack/path。

## 验证策略

OpenSpec 阶段：

- `openspec validate plugin-detail-api-v1 --type change --strict --json`

后续实现阶段至少需要覆盖：

- detail 主资源和四个子资源的 envelope / 404 / forbidden / unavailable 语义。
- secret、path、entrypoint、内部错误的脱敏断言。
- `allowed_actions` 与 `action_state_hints` 不等于实际动作执行的契约边界。
- 与 Registry V1 身份字段的一致性，以及与 SourceBinding/runtime inspect 的边界不重叠。
