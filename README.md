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

## 本地运行入口

当前后端不是单一进程架构。`api`、`worker`、`scheduler` 是三个独立入口：

- `uv run api`
  只启动 FastAPI HTTP 服务
- `uv run quantagent-worker`
  启动后台消费入口，负责消费 `source.event.captured`、做后置 Readability 正文增强，并发布 `industry.analysis.requested`
- `uv run quantagent-scheduler`
  启动调度入口，负责扫描 due `SourceBinding`、触发 `source.fetch`、写 `SchedulerRun` 并发布 `source.event.captured`

这意味着：

- 只执行 `uv run api` 不会自动带起 `worker` 和 `scheduler`
- 如果要验证 `RSS -> source.event.captured -> worker -> industry.analysis.requested` 主链路，需要至少同时运行数据库、scheduler 和 worker
- 默认 `EVENT_BUS_BACKEND=memory` 只适合单进程测试或单测；`scheduler` 和 `worker` 分开进程运行时，`memory` backend 不能跨进程传消息

### 本地最小启动建议

只看 API：

```bash
APP_ENV=development uv run api
```

看 scheduler 单次调度 smoke：

```bash
DATABASE_URL='postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent' \
EVENT_BUS_BACKEND=memory \
uv run python -c 'import asyncio; from quantagent.scheduler.main import run_once; print(asyncio.run(run_once()))'
```

看 worker 单次消费 smoke：

```bash
DATABASE_URL='postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent' \
EVENT_BUS_BACKEND=memory \
uv run python -c 'import asyncio; from quantagent.worker.main import run_once; asyncio.run(run_once())'
```

说明：

- 上面两个 `run_once()` 只适合各自单独 smoke；如果 `EVENT_BUS_BACKEND=memory`，两者分开运行不会共享事件
- 真正的跨进程端到端链路需要 Kafka backend

### 本地端到端建议

1. 启动数据库：

```bash
docker compose up -d db
```

2. 迁移数据库：

```bash
DATABASE_URL='postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent' uv run quantagent-db upgrade
```

3. 如果要跑跨进程 event bus，启用 Kafka profile：

```bash
docker compose --profile kafka up -d kafka
```

4. 分别启动 scheduler 和 worker：

```bash
DATABASE_URL='postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent' \
EVENT_BUS_BACKEND=kafka \
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
uv run quantagent-scheduler
```

```bash
DATABASE_URL='postgresql+psycopg://quantagent:quantagent@localhost:15432/quantagent' \
EVENT_BUS_BACKEND=kafka \
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
uv run quantagent-worker
```

如果只想验证调度能否真实抓到 RSS，可以只跑数据库 + scheduler，不必带 worker。

## 半导体 RSS 主链路现状

截至 2026-06-02，这条主链路已经具备以下可运行结论：

- `uv run api` 只启动 HTTP 服务，不会自动抓 RSS，也不会自动消费 `source.event.captured`
- `scheduler` 需要单独启动，负责抓 RSS、写 `SchedulerRun`、发布 `source.event.captured`
- `worker` 需要单独启动，负责消费 `source.event.captured`、尝试 Readability、再发布 `industry.analysis.requested`
- `EVENT_BUS_BACKEND=memory` 只能证明单进程内链路；`scheduler` 和 `worker` 分开进程时，必须改用 Kafka

### 已验证的实际运行结果

- 2026-06-02 使用 PostgreSQL 本地库做真实 smoke，`scheduler.run_once()` 对 `binding-semiconductor-rss-smoke` 抓取 `https://blogs.nvidia.com/feed/` 在配置 `max_response_bytes=1048576` 后成功返回：
  - `status=succeeded`
  - `captured_count=5`
  - `event_published=true`
- 同日做了同进程 `memory` bus harness：
  - 手工发布 `source.event.captured`
  - worker 成功解析 owner=`industry:semiconductor`
  - Readability 失败时仍然走 degraded 路径
  - worker 成功发布 `industry.analysis.requested`

这说明当前仓库已经能证明：

- 调度侧可以真实抓到 RSS 并发布 capture 事件
- worker 侧可以消费 capture 事件并继续向下游 topic handoff
- 如果你只执行 `uv run api`，看不到这条链路

### 已复核的半导体 RSS 推荐源

推荐 baseline required/default-enabled：

| Feed | 说明 |
| --- | --- |
| `https://investors.micron.com/rss/news-releases.xml` | 官方 IR feed，当前环境可访问，默认大小限制内可直接抓取 |
| `https://investor.marvell.com/news-events/press-releases/rss` | 官方 IR feed，当前环境可访问，默认大小限制内可直接抓取 |
| `https://semiengineering.com/feed/` | 半导体垂直媒体 feed，当前环境可访问，默认大小限制内可直接抓取 |
| `https://newsroom.intel.com/feed/` | 官方 newsroom feed，当前环境可访问，适合作为基础覆盖 |

推荐 expansion optional：

| Feed | 说明 |
| --- | --- |
| `https://blogs.nvidia.com/feed/` | 官方 feed，但响应体偏大；需要 `max_response_bytes=1048576` |
| `https://www.tomshardware.com/feeds/all` | 真 RSS，但噪音高于 baseline |
| `https://www.eetimes.com/feed/` | 行业媒体 feed，适合作为扩展覆盖 |
| `https://export.arxiv.org/rss/cs.AR` | 研究向 RSS，适合补充技术前沿 |

当前不建议直接放进默认模板的候选：

| Feed | 原因 |
| --- | --- |
| `https://export.arxiv.org/rss/cs.LG` | 当前环境是真 RSS，但响应体约 1.9MiB，超过插件 schema 上限 |
| `https://www.digitimes.com/rss/daily.xml` | 当前环境可访问，但条目量更大，V1 先不放进默认 optional 模板 |
| `https://www.anandtech.com/rss/` | 当前环境返回 HTML 页面，不是真 feed |
| `https://investor.amd.com/rss/news-releases.xml` | 当前环境 TLS 握手不稳定 |
