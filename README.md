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

`docker-compose.yml` 通过环境变量插值读取配置，并带有本地开发默认值；`.env.example` 用于展示和覆盖这些默认值。宿主机访问数据库使用 `DATABASE_URL`，API 容器内部访问数据库使用 `API_DATABASE_URL`。

启动本地 PostgreSQL 17：

```bash
docker compose up -d db
```

Compose 内部连接地址为 `db:5432`；宿主机默认绑定 `127.0.0.1:15432`，避免和本机已有 PostgreSQL 的 `5432` 端口冲突，也避免暴露到局域网。如需调整，可以在 `.env` 中设置 `DB_HOST` 和 `DB_PORT`。

API 容器内固定监听 `8000`，宿主机默认绑定 `127.0.0.1:8000`，可通过 `.env` 中的 `API_BIND_HOST` 和 `API_PORT` 调整。

构建并启动后端 API 与数据库：

```bash
docker compose up --build api
```

API 容器使用根目录 `Dockerfile` 的分步构建，最终镜像只包含运行后端所需的 Python 虚拟环境。

服务器或本地需要执行数据库迁移时，先构建镜像，再显式运行一次性迁移服务：

```bash
docker compose build api
docker compose --profile migration run --rm migrate
```

`migrate` 服务默认不会随 `docker compose up api` 自动运行，避免本地启动 API 时隐式修改数据库结构。

如果修改了 `POSTGRES_DB`、`POSTGRES_USER` 或 `POSTGRES_PASSWORD`，请同步调整 `API_DATABASE_URL` 和 `MIGRATION_DATABASE_URL`。

本地直跑数据库迁移命令由 `packages/core` 提供，API 启动流程不负责自动迁移：

```bash
uv run quantagent-db upgrade
uv run quantagent-db current
uv run quantagent-db check
```

如果依赖仓库根目录 `.env` 中的 `DATABASE_URL`，请从仓库根目录运行这些 `uv run` 命令。若在 `packages/core` 或其他子目录执行，需要显式提供 `DATABASE_URL`，或改用 `uv run quantagent-db --database-url <DATABASE_URL> upgrade` 这类带参数的调用。服务器或容器中如果已经把 `quantagent-db` 安装进虚拟环境或镜像 `PATH`，命令默认会从当前目录及其祖先目录尝试定位 `packages/core/alembic.ini` 和 `packages/core/alembic/`；如果部署目录不保留这类仓库结构，需要通过 `QUANTAGENT_CORE_MIGRATION_ROOT=/path/to/packages/core` 显式指定迁移目录。
