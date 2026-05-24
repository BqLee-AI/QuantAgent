# 10. 插件管理页

## 页面定位

插件管理页用于集中查看已安装插件、类型、版本、状态和最近错误，并进入插件详情页进行配置或排障。它是系统治理页，不承担操盘主链路，但会直接影响事件采集和分析质量。

页面主对象是**插件**。

## 页面目标

- 告诉用户系统当前有哪些 Source / Industry / Strategy / Notification / Executor 插件。
- 让用户快速发现异常插件。
- 提供进入配置、依赖查看和审计的入口。
- 帮助用户判断系统问题是否来自插件异常。

## 入口与出口

### 入口

- 顶部导航“插件”
- Dashboard 或运行看板中的插件异常提醒

### 出口

- 插件详情页
- 返回运行看板

## 页面布局

建议采用：

```text
页面头
  -> 插件概览条
  -> 类型与状态筛选栏
  -> 插件列表
  -> 健康与错误摘要区
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 说明治理定位 | `features/plugins/components/PluginsPageHeader` |
| 插件概览条 | 展示插件整体规模与状态 | `features/plugins/components/PluginSummaryBar` |
| 筛选栏 | 按类型、状态、来源筛选 | `features/plugins/components/PluginFilterBar` |
| 插件列表 | 展示插件核心字段 | `features/plugins/components/PluginList` |
| 健康与错误摘要区 | 提醒系统关键插件问题 | `features/plugins/components/PluginAlertsPanel` |

## 模块详细要求

### 1. 页面头

展示：

- 标题：`插件管理`
- 副标题：解释该页是治理页，而非插件市场

### 2. 插件概览条

建议展示：

- 已安装插件数
- 启用插件数
- warning / error 插件数
- 最近 24 小时异常数

### 3. 筛选栏

建议条件：

- 类型：source / industry / strategy / notification / executor
- 状态：enabled / disabled / warning / error
- 来源：official / third-party / runtime

### 4. 插件列表

每条必须展示：

- 插件名
- 类型
- 版本
- 来源
- 状态
- 最近错误
- 详情入口

### 5. 健康与错误摘要区

展示：

- 最近失败最多的插件
- 配置校验失败的插件
- 依赖缺失的插件

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 正常 | 显示完整列表 |
| 无插件 | 显示空态 |
| 局部异常 | 对应行高亮 warning / error |
| 加载失败 | 展示错误和重试入口 |

## 示例

```text
插件管理
已安装：12
启用：9
异常：2

- ReutersSource source v0.3 enabled healthy
- OilIndustryPackage industry v0.2 enabled warning
```

## 推荐前端模块拆分

- `PluginsPageHeader`
- `PluginSummaryBar`
- `PluginFilterBar`
- `PluginList`
- `PluginListRow`
- `PluginAlertsPanel`

## 非目标

- 不做插件市场
- 不做第三方前端注入
- 不做插件开发工作台
