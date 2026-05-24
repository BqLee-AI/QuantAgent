# 14. Industries 页

## 页面定位

Industries 页用于展示行业包摘要、Source Binding、工具摘要和市场映射，是行业包治理和巡检页面。它帮助用户理解系统当前的行业覆盖范围和行业分析装配情况。

页面主对象是**Industry Package**。

## 页面目标

- 让用户知道当前有哪些行业包处于启用状态。
- 让用户快速理解行业包覆盖哪些数据源、哪些工具、哪些市场。
- 帮助用户从治理视角判断某个事件为何会被路由到某些行业。
- 为未来扩行业包提供清晰的检查入口。

## 入口与出口

### 入口

- 顶部导航“行业包”
- 事件详情中的行业标签或行业摘要
- 插件详情中的行业包入口

### 出口

- 返回事件详情
- 返回插件详情
- 返回运行看板

## 页面布局

建议采用：

```text
页面头
  -> 概览条
  -> 行业包列表
  -> 市场映射摘要区
  -> 说明区（可选）
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 解释行业包作用 | `features/industries/components/IndustriesPageHeader` |
| 概览条 | 展示行业包总体状态 | `features/industries/components/IndustrySummaryBar` |
| 行业包列表 | 展示行业包摘要 | `features/industries/components/IndustryList` |
| 市场映射摘要区 | 展示资产映射与覆盖范围 | `features/industries/components/MarketMappingPanel` |
| 说明区 | 解释行业包、Source Binding 和 Tool 的关系 | `features/industries/components/IndustryHelpPanel` |

## 模块详细要求

### 1. 页面头

展示：

- 标题：`行业包`
- 副标题：说明行业包是事件分析的领域单元

### 2. 概览条

建议展示：

| 指标 | 说明 |
| --- | --- |
| 行业包总数 | 当前注册的行业包数量 |
| 启用行业包数 | 当前可用行业包数量 |
| 覆盖市场数 | 已映射的市场对象数量 |
| 异常行业包数 | 配置或依赖异常数量 |

### 3. 行业包列表

每条至少展示：

| 字段 | 说明 |
| --- | --- |
| 行业包名 | 唯一标识 |
| 状态 | enabled / disabled / warning |
| 覆盖行业 | 该包主要负责哪些领域 |
| Source Binding 数 | 绑定数据源数量 |
| Tool 数 | 行业包可用工具数 |
| 最近使用 | 最近一次被路由到的时间 |

建议行操作：

- 查看市场映射摘要
- 查看关联插件

### 4. 市场映射摘要区

展示：

- 该行业包映射的核心标的
- 主要市场
- 典型影响对象

### 5. 说明区

说明：

- 行业包不是一个普通标签，而是分析装配单元
- 行业包可能组合 Source Binding、Skill、Tool 和 market mapping

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 正常 | 显示列表和映射摘要 |
| 无行业包 | 空态 |
| 异常 | 对应行高亮 warning / error |

## 示例

```text
OilIndustryPackage
状态：enabled
覆盖行业：原油 / 航运 / 油服
来源绑定：3
工具：2
最近使用：09:16
映射市场：Brent / WTI / XLE
```

## 推荐前端模块拆分

- `IndustriesPageHeader`
- `IndustrySummaryBar`
- `IndustryList`
- `IndustryListRow`
- `MarketMappingPanel`
- `IndustryHelpPanel`

## 对应数据建议

```ts
type IndustryPackageListItem = {
  id: string
  name: string
  status: 'enabled' | 'disabled' | 'warning'
  coveredDomains: string[]
  sourceBindingCount: number
  toolCount: number
  lastUsedAt?: string
  mappedMarkets: string[]
}
```

## 非目标

- 不做行业包图形化编排器
- 不做行业知识编辑器
- 不做策略回测工作台
