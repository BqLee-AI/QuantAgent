# 11. 插件详情页

## 页面定位

插件详情页用于查看单个插件的状态、配置、依赖、错误和审计记录，是插件治理的核心详情页。

页面主对象是**插件**。

## 页面目标

- 让用户知道插件是否可用、为什么不可用。
- 支持 schema-driven 配置查看与编辑。
- 支持启用、停用、重载等运维动作。
- 让用户理解插件与事件分析链路的关系。

## 入口与出口

### 入口

- 从插件管理页进入
- 从运行看板或错误提醒中进入

### 出口

- 返回插件列表
- 返回运行看板

## 页面布局

建议采用：

```text
页面头
  -> 插件概览卡
  -> 左右双栏
     左：配置表单 / 依赖关系
     右：健康状态 / 错误 / 运维动作
  -> 底部：审计记录
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 标识插件对象 | `features/plugins/components/PluginDetailHeader` |
| 插件概览卡 | 展示类型、版本、来源、状态 | `features/plugins/components/PluginOverviewCard` |
| 配置表单区 | schema-driven 配置 | `features/plugins/components/PluginConfigPanel` |
| 依赖关系区 | 展示上游和下游依赖 | `features/plugins/components/PluginDependencyPanel` |
| 健康与错误区 | 展示健康摘要和错误 | `features/plugins/components/PluginHealthPanel` |
| 运维动作区 | enable / disable / reload | `features/plugins/components/PluginOpsPanel` |
| 审计记录区 | 展示配置或状态变更 | `features/plugins/components/PluginAuditPanel` |

## 模块详细要求

### 1. 插件概览卡

展示：

- 插件名
- 类型
- 版本
- 来源
- 当前状态

### 2. 配置表单区

要求：

- 从 `config-schema` 驱动
- sensitive 字段只显示 masked value 或 secret reference
- 保存前可做 validate

### 3. 依赖关系区

展示：

- 上游 Source Binding
- 所需 Skill / Tool
- 关键下游使用方

### 4. 健康与错误区

展示：

- 最近错误
- 最近恢复时间
- 健康状态

### 5. 运维动作区

按钮：

- 启用
- 停用
- 重载

交互要求：

- 高风险动作要确认
- 操作结果写入审计记录

### 6. 审计记录区

展示：

- 配置变更
- 状态变更
- reload 记录

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| enabled | 展示正常状态 |
| disabled | 配置可见但行动受限 |
| warning | 高亮问题说明 |
| error | 高亮错误与最近失败 |

## 示例

```text
OilIndustryPackage
状态：enabled
版本：0.2.1
依赖：ReutersSource, OPECCalendarSource
最近错误：无
```

## 推荐前端模块拆分

- `PluginDetailHeader`
- `PluginOverviewCard`
- `PluginConfigPanel`
- `PluginDependencyPanel`
- `PluginHealthPanel`
- `PluginOpsPanel`
- `PluginAuditPanel`

## 非目标

- 不允许插件注入自定义前端组件
- 不做插件开发 IDE
