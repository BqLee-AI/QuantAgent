# 13. Tools 页

## 页面定位

Tools 页用于查看 Tool Registry 中的工具摘要、来源插件、schema、权限状态和最近错误。它是工具治理索引页，用于解释 Agent 可调用的受控能力边界。

页面主对象是**Tool**。

## 页面目标

- 告诉用户系统当前有哪些工具可被 Agent 使用。
- 明确工具是否被授权与是否健康。
- 让用户理解工具和 Skill 的区别。
- 为运行失败或分析不稳定提供治理入口。

## 入口与出口

### 入口

- 顶部导航“工具”
- Agent Run 详情中的工具摘要入口
- Tool Invocation 详情中的回溯入口

### 出口

- Tool Invocation 详情
- 返回运行看板
- 返回 Agent Run 详情

## 页面布局

建议采用：

```text
页面头
  -> Tools 概览条
  -> 筛选栏
  -> Tools 列表
  -> 底部说明区（可选）
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 定义页面作用 | `features/tools/components/ToolsPageHeader` |
| Tools 概览条 | 展示总量与授权情况 | `features/tools/components/ToolSummaryBar` |
| 筛选栏 | 来源与权限筛选 | `features/tools/components/ToolFilterBar` |
| Tools 列表 | 展示核心字段 | `features/tools/components/ToolList` |
| 说明区 | 解释 Tool 与 Skill / Plugin 的关系 | `features/tools/components/ToolHelpPanel` |

## 模块详细要求

### 1. 页面头

展示：

- 标题：`Tools`
- 副标题：说明这里展示的是受控工具注册表，不是自由脚本列表

### 2. Tools 概览条

建议展示：

| 指标 | 说明 |
| --- | --- |
| Tool 总数 | Registry 中的 Tool 数量 |
| 已授权 Tool 数 | 当前可调用的 Tool 数量 |
| schema 异常数 | schema 无效或缺失数量 |
| 最近失败 Tool 数 | 最近 24 小时出错的 Tool 数量 |

### 3. 筛选栏

建议筛选条件：

- 来源：core / plugin / runtime
- 权限状态：granted / blocked / restricted
- schema 状态：valid / invalid

### 4. Tools 列表

每条 Tool 至少展示：

| 字段 | 说明 |
| --- | --- |
| Tool 名称 | 唯一标识 |
| 来源插件 | 若来自插件则展示 |
| 权限状态 | 当前是否可被调用 |
| schema 状态 | 参数 schema 是否正常 |
| 最近错误 | 最近一次错误摘要 |
| 最近调用时间 | 最近一次被 Agent 调用的时间 |

建议行操作：

- 查看最近调用
- 查看来源插件

### 5. 说明区

说明：

- Tool 用于受控外部动作或查询
- Tool 不等于 Skill
- Tool 是否可用受权限和 schema 状态共同影响

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 正常 | 显示列表 |
| 无工具 | 空态 |
| schema 异常 | 行内高亮 invalid |
| 权限受限 | 行内高亮 restricted / blocked |

## 示例

```text
NewsVerificationTool
来源：core
权限：granted
schema：valid
最近错误：1 次超时
最近调用：09:16
```

## 推荐前端模块拆分

- `ToolsPageHeader`
- `ToolSummaryBar`
- `ToolFilterBar`
- `ToolList`
- `ToolListRow`
- `ToolHelpPanel`

## 对应数据建议

```ts
type ToolListItem = {
  id: string
  name: string
  provider: 'core' | 'plugin' | 'runtime'
  providerPluginName?: string
  permissionStatus: 'granted' | 'blocked' | 'restricted'
  schemaStatus: 'valid' | 'invalid'
  recentErrorSummary?: string
  lastInvokedAt?: string
}
```

## 非目标

- 不做 Tool 开发台
- 不做自由脚本执行器
- 不做参数 schema 编辑器
