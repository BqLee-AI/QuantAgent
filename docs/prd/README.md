# QuantAgent PRD 总索引

**版本**：v1.2.0  
**状态**：与设计同步的正式整理稿  
**核心架构**：FastAPI + DeepAgents + React + PostgreSQL + 插件运行时

## 产品摘要

QuantAgent 是一款面向专业交易者和研究员的事件驱动型量化智能系统。系统以事件流为主线，通过 Source Plugin 采集外部信息，经 Router Agent 路由到行业包，再由 AgentRuntime、Scoring / Debate 和 Decision / Policy Gate 形成可审计的通知、人工确认、dry-run 或受控执行结果。

系统采用插件化架构：Source、Industry、Strategy、Notification、Executor 都以 `plugin.yaml` 注册，Registry、ToolRegistry、Skill Registry 和 runtime 目录共同承担运行时治理。

## 模块化文档

| 序号 | 模块 | 文档 | 核心内容 |
| --- | --- | --- | --- |
| 01 | 产品概览 | [01-overview.md](01-overview.md) | 产品定位、目标用户、范围边界 |
| 02 | 行业场景 | [02-industry-scenarios.md](02-industry-scenarios.md) | 石油、半导体/内存等行业包场景 |
| 03 | 功能模块 | [03-functional-modules.md](03-functional-modules.md) | Source、Router、Industry、Decision、Approval |
| 04 | 技术架构 | [04-technical-architecture.md](04-technical-architecture.md) | 后端、前端、数据库、插件、WebSocket、部署 |
| 05 | UX 需求 | [05-ux-requirements.md](05-ux-requirements.md) | 运行时管理台、审批工作台、插件后台 |
| 06 | 风控约束 | [06-risk-constraints.md](06-risk-constraints.md) | 验证、隐私、熔断、执行边界、审计 |
| 07 | 验收与待确认 | [07-acceptance-open-questions.md](07-acceptance-open-questions.md) | 验收标准、测试重点、待确认问题 |
| 08 | 操盘者工作台页面与治理信息架构 | [08-frontend-pages-overview.md](08-frontend-pages-overview.md) | 页面主链路、优先级、治理对象层级、页面附录入口 |
| 09 | 评分体系与优先级 | [09-scoring-and-prioritization.md](09-scoring-and-prioritization.md) | 事件、分析、建议评分与高价值事件判定 |

## 模块依赖

```text
外部事件源
  -> Source Plugin / RawEvent
  -> Event Bus
  -> Router Agent
  -> Industry Plugin / AgentRuntime / ToolRegistry / Skill Registry
  -> Scoring / Debate
  -> Decision / Policy Gate
  -> Notification / Human Approval / Executor
  -> Persistence / Audit / WebSocket 更新
  -> React 前端管理台
```

## 已确认事实

- 系统目标是事件驱动型量化分析，不是通用聊天机器人。
- 行业包是插件化能力单元，必须通过 Registry 注册和治理。
- 初版实时通道采用 Native WebSocket，REST 仍是业务状态真源。
- 插件配置采用 schema-driven form，前端不接收插件自定义组件。
- 真实执行必须经过 Decision / Policy Gate，不由前端按钮直接决定。
- 部署目标为 Docker，初版保留 api、worker、scheduler、web 四类入口。

## 阅读建议

- 产品/业务评审：先读 [产品概览](01-overview.md)、[行业场景](02-industry-scenarios.md)。
- 技术方案评审：先读 [功能模块](03-functional-modules.md)、[技术架构](04-technical-architecture.md)。
- 交互评审：先读 [UX 需求](05-ux-requirements.md)、[风控约束](06-risk-constraints.md)。
- 页面评审：先读 [操盘者工作台页面与治理信息架构](08-frontend-pages-overview.md)，再进入 `pages/` 页面附录。
