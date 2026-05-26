# 11. Plugin Detail

## 页面定位

Plugin Detail 是单个插件的治理页，用于查看插件版本、配置、依赖、提供的能力、健康状态、运行错误和审计记录。

不同类型插件共享同一详情页骨架，但详情 tab 内容按插件类型变化。

## 用户任务

- 判断插件是否可用，以及为什么不可用。
- 查看和编辑 schema-driven 配置。
- 检查依赖、SourceBinding、提供的 Skill / Tool / market mapping。
- 执行启用、停用、reload 等受控运维动作。
- 查看配置和生命周期审计。

## 主对象和真源

主对象是 PluginRecord。

| 信息 | 真源 |
| --- | --- |
| 插件概览 | plugin_records / plugin_versions |
| 配置 | plugin_configs + config_schema |
| 依赖 | plugin_dependency_records |
| 提供能力 | manifest / Registry 摘要 |
| 健康状态 | Registry health / runtime_errors |
| 审计 | audit_logs |

## 页面结构

```text
页面头
  -> Overview
  -> Config
  -> Dependencies
  -> Provided Capabilities
  -> Health
  -> Audit
  -> Ops
```

## 通用 tab

### Overview

展示：

- plugin_id。
- name。
- type。
- source。
- installed_version。
- status。
- active_version。
- active config 状态。
- blocked_reason。
- last_error。

### Config

规则：

- 通过 JSON Schema form 渲染。
- 敏感字段只显示 masked value 或 secret reference。
- 保存前调用 validate。
- 保存后创建新配置快照并写审计。
- 配置是否需要 reload 由 manifest / Registry 决定。

### Dependencies

展示：

- plugin dependencies。
- python dependencies。
- system dependencies。
- required / optional。
- status。
- blocked reason。
- reverse dependencies。

### Provided Capabilities

按插件类型展示该插件提供或注册的能力：

- Source：fetch / subscribe / normalize 能力和 SourceBinding 使用情况。
- Industry：AgentDefinition、Skill、Tool、MarketMapping、scoring hints。
- Strategy：action generation、validate_action、risk flags。
- Notification：send 能力、渠道、送达状态。
- Broker：dry_run / mock 能力和 disabled 状态。

Skill 和 Tool 在这里作为插件提供能力展示，不作为顶层管理对象。

### Health

展示：

- health_check 结果。
- 最近错误。
- 关联 runtime_errors。
- 最近使用或调用摘要。

### Audit

展示：

- 安装、升级、降级、启用、停用、reload。
- 配置变更。
- 依赖自动安装。
- 失败或阻断。

### Ops

允许的动作：

- enable。
- disable。
- reload。
- uninstall，若后续允许。

交互要求：

- 高风险动作二次确认。
- broker 类型必须明确初版只支持 disabled / dry_run / mock。
- 启用前必须显示依赖和配置检查结果。
- 所有动作写审计。

## 类型化重点

| 类型 | 详情页重点 |
| --- | --- |
| source | 采集配置、噪音熔断、最近抓取错误、被哪些 industry 使用 |
| industry | SourceBinding、AgentDefinition、Skill、Tool、MarketMapping、最近命中事件 |
| strategy | 策略建议生成、risk flags、Decision 输入摘要 |
| notification | 通知渠道、送达失败、secret reference |
| broker | disabled / dry_run / mock、Policy Gate、权限和最近 dry_run |

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| installed_but_blocked | Overview 置顶显示阻塞原因 |
| config_invalid | Config tab 高亮校验错误 |
| dependency_missing | Dependencies tab 高亮缺失依赖 |
| failed | Health tab 展示 last_error 和 runtime error |
| broker disabled | Ops tab 解释不能执行任何动作 |
| 权限不足 | 禁用操作，显示 capability 缺失 |

## 安全边界

- 不展示 secret 原文。
- 不展示完整私有策略。
- 不允许插件注入自定义前端组件。
- broker 配置不得暗示真实执行已支持。
- 插件卸载不得删除历史事件、分析、审批和审计记录。

## 验收口径

必须成立：

- 用户能判断插件当前是否可用。
- 用户能看到阻塞来自配置、依赖、权限还是运行错误。
- 用户能理解 Industry 插件如何提供 Skill / Tool / MarketMapping。
- 用户能看到 broker 初版只支持 disabled / dry_run / mock。

失败信号：

- 插件详情只是字段列表，没有依赖和能力层级。
- Skill 和 Tool 被误导成需要独立顶层管理。
- 配置保存没有 validate 和审计语义。

## 非目标

- 不做插件开发 IDE。
- 不做插件市场。
- 不做 Skill 内容编辑器。
- 不做 Tool schema 编辑器。
- 不做生产实盘执行配置中心。
