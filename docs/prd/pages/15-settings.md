# 15. 设置页

## 页面定位

设置页用于管理会话、通知偏好、实时连接偏好、局部风险开关和系统级展示偏好。它只承接前端使用体验和少量系统级展示偏好，不承接业务核心规则。

页面主对象是**系统设置 / 用户偏好**。

## 页面目标

- 让用户管理个人使用偏好和少量系统级设置。
- 避免把高风险策略控制和业务核心规则塞进设置页。
- 提供一个可解释、可恢复默认值的偏好管理入口。

## 入口与出口

- 顶部导航“设置”
- 从登录状态区或通知设置入口进入

## 页面模块

| 模块 | 作用 | 推荐前端模块 |
| --- | --- | --- |
| 页面头 | 解释设置边界 | `features/settings/components/SettingsPageHeader` |
| 会话与身份区 | 展示当前 actor 和会话状态 | `features/settings/components/SessionPanel` |
| 通知偏好区 | 管理提醒方式 | `features/settings/components/NotificationPrefsPanel` |
| 实时连接偏好区 | 管理自动刷新与断连提示 | `features/settings/components/RealtimePrefsPanel` |
| 风险提示开关区 | 管理仅影响前端提示的开关 | `features/settings/components/RiskUiPanel` |

## 功能明细

### 会话与身份区

展示：

- 当前 actor
- 当前环境
- 登录状态
- 退出登录

### 通知偏好区

展示：

- UI 内提醒开关
- 声音提醒开关
- 关键审批提醒开关

### 实时连接偏好区

展示：

- 自动刷新开关
- 断线提醒开关
- 降级刷新提示

### 风险提示开关区

只允许影响前端提示体验，例如：

- 高风险审批高亮
- 到期审批闪烁提醒

## 页面状态设计

| 状态 | 页面行为 |
| --- | --- |
| 正常 | 展示设置项 |
| 保存中 | 对应模块 loading |
| 保存失败 | 模块级错误提示 |

## 示例

```text
当前身份：trader_admin
通知：UI 内提醒已开启
实时连接：断线提示已开启
高风险审批高亮：已开启
```

## 推荐前端模块拆分

- `SettingsPageHeader`
- `SessionPanel`
- `NotificationPrefsPanel`
- `RealtimePrefsPanel`
- `RiskUiPanel`

## 非目标

- 不做真实账户密钥管理中心
- 不做策略引擎配置总后台
- 不做生产风控规则编辑器
