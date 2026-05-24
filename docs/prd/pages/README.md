# 前端页面文档索引

## 使用方式

这一组文档是 `08-frontend-pages-overview.md` 的展开层，用于把每个页面拆成可以继续画线框、写 OpenSpec、拆 issue 和实现组件的粒度。

阅读顺序建议：

1. 先看 [前端页面规划总览](../08-frontend-pages-overview.md)
2. 再看 P0 页面
3. 最后看 P1 / P2 支撑页面

## P0 页面

- [00 Dashboard 首页](00-dashboard.md)
- [01 登录页](01-login.md)
- [02 高价值事件首页](02-events-home.md)
- [03 事件详情 / 决策页](03-event-detail.md)
- [04 审批工作台](04-approvals-index.md)

## P1 页面

- [16 事件级审计时间线](16-event-audit-timeline.md)
- [05 审批详情页](05-approval-detail.md)
- [06 一次性授权页](06-approval-link.md)
- [07 运行看板](07-runtime-dashboard.md)
- [08 Agent Run 详情](08-runtime-agent-run-detail.md)
- [09 Tool Invocation 详情](09-runtime-tool-detail.md)
- [10 插件管理页](10-plugins-index.md)
- [11 插件详情页](11-plugin-detail.md)

## P2 页面

- [12 Skills 页](12-skills.md)
- [13 Tools 页](13-tools.md)
- [14 Industries 页](14-industries.md)
- [15 设置页](15-settings.md)

## 统一写法说明

每个页面文档默认包含以下部分：

- 页面定位：说明这个页面存在的原因。
- 页面目标：说明用户到这个页面要完成什么。
- 入口与出口：说明从哪里进入、处理完后去哪里。
- 页面模块：说明页面由哪些模块构成，以及建议拆到哪些前端组件。
- 功能明细：逐模块写清楚展示、交互、状态、风险边界。
- 示例：用具体场景示意页面长什么样、用户怎么用。
- 非目标：防止后续把未来阶段能力混进来。
