# QuantAgent 文档中心

本文档中心分为两层：`docs/design/` 是最终设计真相来源，`docs/prd/` 是按设计同步后的产品需求与索引。

## Demo 演示

| Demo | 说明 |
| --- | --- |
| [quantagent-demo CLI](demo/quantagent-demo-cli.md) | 最小闭环：插件扫描 → 触发 → 事件发布 → 消费 |
| [插件底座 Demo](demo/plugin-registry-v1-pseudocode.md) | Registry → Runtime → Scheduling 全链路说明 |

## 设计文档索引

| 序号 | 文档 | 作用 |
| --- | --- | --- |
| 01 | [技术栈与项目结构](design/01-tech-stack-and-project-structure.md) | 技术栈、monorepo 结构、插件目录与契约边界 |
| 02 | [核心架构与运行时](design/02-core-architecture-and-runtime.md) | 事件驱动主流程、Event 模型、Decision / Policy Gate |
| 03 | [插件系统与 Registry](design/03-plugin-system-and-registry.md) | 插件类型、`plugin.yaml`、注册与生命周期 |
| 04 | [数据库与持久化](design/04-database-and-persistence-design.md) | PostgreSQL、SQLAlchemy 2.x、Alembic、审计与敏感配置 |
| 05 | [Agent 工作流](design/05-agent-workflow-design.md) | AgentRuntime、DeepAgents、ToolRegistry、Skill Registry |
| 06 | [Source Plugin](design/06-source-plugin-design.md) | 数据源插件、SourceBinding、调度与原文读取 |
| 07 | [Industry Package](design/07-industry-package-design.md) | 行业包组合插件、行业 Agent、市场映射、评分提示 |
| 08 | [API 与实时通道](design/08-api-and-websocket-design.md) | FastAPI、REST、WebSocket、插件配置与审批接口 |
| 09 | [前端架构](design/09-frontend-architecture-design.md) | React + Vite、路由、状态、审批和运行时面板 |
| 10 | [部署与 Runtime](design/10-deployment-and-runtime-design.md) | Docker、runtime 目录、迁移、健康检查、Redis 演进 |
| 11 | [Crawler Source Plugin 边界](design/11-crawler-source-plugin-boundary.md) | crawler 类 Source Plugin 的配置、运行时和 reader fallback 职责边界 |

## PRD 索引

| 序号 | 文档 | 作用 |
| --- | --- | --- |
| 01 | [产品概览](prd/01-overview.md) | 产品定位、目标用户、范围边界 |
| 02 | [行业场景与插件包](prd/02-industry-scenarios.md) | 石油、半导体/内存等行业包场景 |
| 03 | [功能模块](prd/03-functional-modules.md) | 事件接入、路由、行业包、审批与运行时 |
| 04 | [技术架构](prd/04-technical-architecture.md) | 后端、前端、数据库、插件、WebSocket、部署 |
| 05 | [UX 与界面需求](prd/05-ux-requirements.md) | 运行时管理台、审批工作台、插件后台 |
| 06 | [风控、约束与异常处理](prd/06-risk-constraints.md) | 验证、权限、噪音熔断、审计与异常处理 |
| 07 | [验收标准与待确认项](prd/07-acceptance-open-questions.md) | 验收口径、测试重点、残余业务问题 |

## 维护约定

- 先更新 `docs/design/`，再同步 `docs/prd/` 与本索引。
- 设计文档中的边界、运行时和插件约束优先于旧 PRD 表述。
- 未确认的业务问题只放在 PRD 的待确认项，不写进设计真相层。
- `runtime/` 下的插件安装内容、本地配置、数据和日志默认不进入 Git；secrets、私有策略、交易密钥和真实 `.env` 不得提交。
