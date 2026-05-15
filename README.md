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
- `packages/core/`：核心基础包，承载共享配置、数据库、Alembic、错误和领域基础能力。
- `packages/agent/`：Agent 与 workflow 包边界预留。
- `packages/plugin-sdk/`：插件开发 SDK 包边界预留。
- `packages/adapters/`：官方 adapter 包边界预留。
- `packages/contracts/`：跨前后端契约与生成物边界预留。

## 本地 Docker 开发

复制环境变量样例后按需调整本地配置：

```bash
cp .env.example .env
```

`.env.example` 只提供本地开发样例，不包含真实密钥；真实 `.env` 不提交到仓库。

启动本地 PostgreSQL 17：

```bash
docker compose up -d db
```

Compose 内部连接地址为 `db:5432`；宿主机默认通过 `localhost:15432` 访问，避免和本机已有 PostgreSQL 的 `5432` 端口冲突。如需改端口，可以在 `.env` 中设置 `DB_PORT`。

构建并启动后端 API 与数据库：

```bash
docker compose up --build api
```

API 容器使用根目录 `Dockerfile` 的分步构建，最终镜像只包含运行后端所需的 Python 虚拟环境。
