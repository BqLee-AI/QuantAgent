# 10. Registry / Plugins

## 页面定位

Registry / Plugins 是 V1 的统一插件治理入口。它管理 `source`、`industry`、`strategy`、`notification`、`broker` 五类插件，不把 Skill、Tool、Industry Package 另外平铺成顶层页面。

## 用户任务

- 查看系统当前安装、启用、失败或被阻塞的插件。
- 按类型、状态、来源筛选插件。
- 发现影响事件采集、分析、通知或虚盘执行的插件问题。
- 进入插件详情配置、检查依赖、查看能力和审计。

## 主对象和真源

主对象是 PluginRecord。

| 信息 | 真源 |
| --- | --- |
| 插件列表 | plugin_records |
| 插件版本 | plugin_versions |
| 插件状态 | Registry / plugin_records |
| 依赖状态 | plugin_dependency_records |
| 配置状态 | plugin_configs 摘要 |
| 错误和审计 | runtime_errors / audit_logs |

## 页面结构

```text
页面头
  -> Registry 概览
  -> 类型视图 tabs
  -> 筛选与排序
  -> 插件列表
  -> 关键阻塞和错误摘要
```

## 类型视图

V1 使用一个统一页面，通过类型 tab 分视图：

- All。
- Sources。
- Industries。
- Strategies。
- Notifications。
- Brokers。

### Sources

关注：

- 采集状态。
- 最近抓取错误。
- 噪音熔断。
- 下游 industry 依赖。

### Industries

关注：

- SourceBinding。
- AgentDefinition。
- 提供的 Skill 和 Tool 摘要。
- MarketMapping 摘要。
- 最近命中事件和失败分析。

Industry Package 是 `industry` 类型插件，不是独立顶层页面。

### Strategies

关注：

- 策略建议生成状态。
- 风险 flags。
- 与 Decision 的边界。

### Notifications

关注：

- 通知渠道状态。
- 送达失败。
- 配置和 secret reference。

### Brokers

关注：

- broker_runtime_mode：disabled / dry_run / mock。
- 初版不支持真实执行。
- 能力、权限和 Policy Gate 约束。
- 最近 dry_run 记录和阻断原因。

## 列表字段

每条插件必须展示：

- 插件名。
- plugin_id。
- type。
- installed_version。
- source。
- status。
- active config 状态。
- 依赖状态摘要。
- last_error。
- 详情入口。

## 操作边界

列表页允许：

- 查看详情。
- 按类型和状态筛选。
- 触发低风险 reload 的入口，是否直接执行由权限决定。

列表页不建议直接做：

- 高风险启用 broker。
- 修改配置。
- 卸载插件。
- 管理 Skill 或 Tool 内容。

高风险动作进入 Plugin Detail 并做二次确认。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| 无插件 | 展示 Registry 为空或扫描未完成 |
| installed_but_blocked | 行内展示阻塞原因 |
| failed | 行内展示 last_error 和详情入口 |
| dependency_missing | 展示缺失依赖摘要 |
| config_invalid | 展示配置无效摘要 |
| broker enabled 风险 | 明确展示初版仅 dry_run / mock |

## 验收口径

必须成立：

- 用户能在一个入口理解插件总体状态。
- 用户能按插件类型治理不同对象。
- Industry、Skill、Tool 的关系不会被误解成平级导航。
- Broker 的 disabled / dry_run / mock 边界清晰。

失败信号：

- 顶层导航同时出现 Plugins、Skills、Tools、Industries，且没有解释层级关系。
- Industry Package 和 Plugin 被当成两个独立主对象。
- Broker 被展示成可真实执行配置。

## 非目标

- 不做插件市场。
- 不做插件开发 IDE。
- 不允许插件注入自定义前端组件。
- 不做 Skill / Tool 顶层管理后台。
