# QuantAgent

QuantAgent 是一套事件驱动的量化智能系统，围绕外部事件采集、行业路由、结构化分析、审批和受控执行构建。

## 文档入口

- [文档中心](docs/README.md)
- [PRD 总索引](docs/prd/README.md)
- [设计文档索引](docs/README.md)

## 当前约定

- 后端：FastAPI
- Agent / Workflow：DeepAgents
- 前端：React + Vite
- 数据库：PostgreSQL
- 部署：Docker
- 插件：`plugin.yaml` + Registry

## 初始目录边界

- `apps/api/`：FastAPI API 入口，负责 HTTP 边界，不承载核心领域逻辑。
- `apps/worker/`：后台任务入口预留，后续承载抓取、路由和长耗时任务。
- `apps/scheduler/`：定时任务入口预留，后续承载周期性调度。
- `packages/quant/core/`：核心基础包边界，后续承载共享配置、数据库、错误和领域基础能力。
- `packages/quant/agent/`：Agent 与 workflow 包边界预留。
- `packages/quant/plugin-sdk/`：插件开发 SDK 包边界预留。
- `packages/quant/adapters/`：官方 adapter 包边界预留。
- `packages/contracts/`：跨前后端契约与生成物边界预留。
