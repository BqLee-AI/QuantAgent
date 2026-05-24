# 12. Skills 页

## 页面定位

Skills 页用于查看 Skill Registry 中的技能包来源、版本、授权状态和最近使用情况，帮助用户理解分析过程中可调用的知识、推理模板和受控能力。

页面主对象是**Skill**。

## 页面目标

- 让用户看到有哪些 Skill 可用。
- 让用户知道 Skill 的来源、版本、授权状态和最近使用情况。
- 让用户在分析解释链路中理解“这次判断调用了哪些知识能力”。
- 为运行异常或分析效果不稳定提供一个知识层治理入口。

## 入口与出口

### 入口

- 顶部导航“技能”
- Agent Run 详情中的 Skill 摘要入口
- 插件详情中的依赖关系区

### 出口

- 返回运行看板
- 返回 Agent Run 详情
- 返回插件详情

## 页面布局

建议采用：

```text
页面头
  -> Skills 概览条
  -> 筛选栏
  -> Skills 列表
  -> 底部说明区（可选）
```

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 定义页面用途 | `features/skills/components/SkillsPageHeader` |
| Skills 概览条 | 展示总量与授权概况 | `features/skills/components/SkillSummaryBar` |
| 筛选栏 | 按来源和授权筛选 | `features/skills/components/SkillFilterBar` |
| Skills 列表 | 展示核心字段 | `features/skills/components/SkillList` |
| 说明区 | 解释 Skill 与 Tool / Plugin 的关系 | `features/skills/components/SkillHelpPanel` |

## 模块详细要求

### 1. 页面头

展示：

- 标题：`Skills`
- 副标题：说明这里展示的是知识和推理能力注册表，不是内容库

示例文案：

```text
Skills
查看系统当前可被 Agent 使用的知识能力、版本与授权状态。
```

### 2. Skills 概览条

建议展示：

| 指标 | 说明 |
| --- | --- |
| Skill 总数 | Registry 中的 Skill 数量 |
| 已授权 Skill 数 | 当前可被使用的 Skill 数 |
| 最近使用 Skill 数 | 最近 24 小时内被使用的 Skill 数 |
| 异常 Skill 数 | 授权异常或元数据异常的 Skill 数 |

### 3. 筛选栏

建议筛选条件：

- 来源：official / plugin / runtime
- 授权状态：enabled / disabled / restricted
- 最近是否使用过：yes / no

### 4. Skills 列表

每条 Skill 至少展示：

| 字段 | 说明 |
| --- | --- |
| Skill 名称 | 唯一标识或展示名 |
| 来源 | 来自官方、插件或运行时 |
| 版本 | 当前版本 |
| 授权状态 | 是否允许 Agent 使用 |
| 最近使用 | 最近一次调用时间 |
| 关联插件 | 如果由插件提供则展示 |

建议行操作：

- 查看来源摘要
- 查看关联插件

### 5. 说明区

建议简短说明：

- Skill 不等于 Tool
- Skill 负责知识和推理模板
- Tool 负责受控外部动作或查询

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 正常 | 显示列表 |
| 无 Skill | 显示空态并说明尚未注册 Skill |
| 数据不可用 | 错误态 |
| 某条异常 | 行内高亮 warning / restricted |

## 示例

```text
OilShockReasoning
来源：official
版本：0.1.0
授权：enabled
最近使用：09:16
关联插件：OilIndustryPackage
```

## 推荐前端模块拆分

- `SkillsPageHeader`
- `SkillSummaryBar`
- `SkillFilterBar`
- `SkillList`
- `SkillListRow`
- `SkillHelpPanel`

## 对应数据建议

```ts
type SkillListItem = {
  id: string
  name: string
  source: 'official' | 'plugin' | 'runtime'
  version: string
  authStatus: 'enabled' | 'disabled' | 'restricted'
  lastUsedAt?: string
  providerPluginName?: string
}
```

## 非目标

- 不做 Skill 编辑器
- 不做 Skill 内容编写后台
- 不做 Skill 训练或调优平台
