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

`docker-compose.yml` 通过环境变量插值读取配置，并带有本地开发默认值；`.env.example` 用于展示和覆盖这些默认值。

默认分两套变量：

- `DATABASE_URL`、`RUNTIME_DIR`
  给宿主机直跑命令使用，例如 `uv run api`、`uv run quantagent-worker`、`uv run quantagent-scheduler`、`uv run quantagent-db upgrade`
- `COMPOSE_DATABASE_URL`、`COMPOSE_RUNTIME_DIR`
  给 Compose 容器内部的 `api`、`worker`、`scheduler`、`migrate` 服务使用

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

如果修改了 `POSTGRES_DB`、`POSTGRES_USER` 或 `POSTGRES_PASSWORD`，请同步调整 `DATABASE_URL` 和 `COMPOSE_DATABASE_URL`。

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
  启动后台消费入口，常驻消费 `source.event.captured`、做后置 Readability 正文增强，继续消费 `industry.analysis.requested`，发布 `industry.analysis.requested` / `event.routed`，并把 Router Agent 结构化输出写入 runtime audit read model
- `uv run quantagent-scheduler`
  启动调度入口，负责扫描 due `SourceBinding`、触发 `source.fetch`、写 `SchedulerRun` 并发布 `source.event.captured`

这意味着：

- 只执行 `uv run api` 不会自动带起 `worker` 和 `scheduler`
- 如果要验证 `RSS -> source.event.captured -> worker -> industry.analysis.requested` 主链路，需要至少同时运行数据库、scheduler 和 worker
- 默认 `EVENT_BUS_BACKEND=kafka`；`memory` 只适合显式覆盖后的单进程测试或单测，不能跨进程传消息

### 本地最小启动建议

推荐先直接复制默认 env：

```bash
cp .env.example .env
```

然后按下面的默认路径启动。只要不改端口，这套默认值就能直接工作。

只看 API：

```bash
uv run api
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
- 默认 `uv run quantagent-worker` 是常驻 worker；只有 `run_once()` 是单条 smoke 入口

### 本地端到端建议

1. 启动数据库：

```bash
docker compose up -d db
```

2. 迁移数据库：

```bash
uv run quantagent-db upgrade
```

3. 安装半导体默认 RSS SourceBinding：

```bash
uv run quantagent-source-bindings install-semiconductor-defaults
```

这个命令会从官方半导体行业包模板生成两个可调度绑定：

- `binding-semiconductor-rss-baseline`：4 个 baseline feed，默认每 300 秒抓一次。
- `binding-semiconductor-rss-expansion`：9 个 expansion feed，默认每 900 秒抓一次。

两者默认都会设为 `active` 并把 `next_run_at` 设为当前时间，方便下一次 scheduler tick 立刻抓取。只想先跑稳定源时可用：

```bash
uv run quantagent-source-bindings install-semiconductor-defaults --no-expansion
```

如果跳过这一步，scheduler 只会扫描数据库里已经存在的绑定；本地库可能只有旧的 `binding-semiconductor-rss-smoke`，它只抓 Micron 单一 RSS，重复 URL 会被 RawEvent 去重，因此 `/runtime` 不会持续新增新闻。

4. 启动 Kafka，供默认 Event Bus 使用：

```bash
docker compose up -d kafka
```

默认 Compose 镜像说明：

- `db` 默认使用 `postgres:17-alpine`，可用 `.env` 中的 `POSTGRES_IMAGE` 覆盖。
- `kafka` 默认使用 `apache/kafka-native:4.0.0`，可用 `.env` 中的 `KAFKA_IMAGE` 覆盖。当前未使用 Kafka Alpine tag，因为 Docker Hub 上没有确认可拉取的 `apache/kafka:4.0.0-alpine`。

5. 分别启动 scheduler 和 worker。默认 env 已经指向 `127.0.0.1:19092`：

```bash
uv run quantagent-scheduler
```

```bash
uv run quantagent-worker
```

如果只想验证调度能否真实抓到 RSS，可以只跑数据库 + scheduler，不必带 worker。

### 抓取是否真的在发生

观察 scheduler stdout 中这些字段：

- `Scheduler tick started: due_bindings=...`
- `Scheduler source fetch succeeded: binding_id=... captured_count=...`
- `Scheduler persisted raw events: total=... created=... duplicate=...`
- `Scheduler published source.event.captured: binding_id=... item_count=...`

如果 `captured_count > 0` 但 `created=0 duplicate>0`，说明 RSS 抓到了条目，但 URL 去重后都是已有新闻；这是正常去重，不是 worker 或 `/runtime` 没工作。

也可以直接查 DB：

```bash
uv run python - <<'PY'
from sqlalchemy import create_engine, text
from quantagent.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    for name, sql in [
        ("source_bindings", "select count(*) from source_bindings"),
        ("scheduler_runs", "select count(*) from scheduler_runs"),
        ("raw_events", "select count(*) from raw_events"),
        ("raw_event_captures", "select count(*) from raw_event_captures"),
        ("event_intake_routed_events", "select count(*) from event_intake_routed_events"),
    ]:
        print(name, conn.execute(text(sql)).scalar())
PY
```

### 事件链路诊断与回放

如果 `/runtime` 没看到新的 Router Agent 输出，先区分是没有新抓取、没有入队、worker 没消费，还是 AI intake 没落库：

```bash
uv run quantagent-source-event-replay diagnose --limit 10
```

该命令会输出运行配置、DB 计数、最近已 capture 但没有 routed read model 的新闻、最近 routed 输出摘要，以及本地 Kafka topic / consumer group 诊断信息。

回测时可以把已入库的 RawEvent/Capture 重新推回 `source.event.captured`，让 worker 重新走 Readability 和 Router Agent：

```bash
# 只预览会重放哪些新闻，不发 Kafka
uv run quantagent-source-event-replay replay --raw-event-id rawevt_xxx --dry-run

# 重放指定 RawEvent
uv run quantagent-source-event-replay replay --raw-event-id rawevt_xxx

# 重放指定 capture
uv run quantagent-source-event-replay replay --capture-id rawevtcap_xxx

# 重放某个 binding 最近 20 条 capture
uv run quantagent-source-event-replay replay --binding-id binding-semiconductor-rss-baseline --limit 20

# 清掉这些 RawEvent 已有的 routed read model，再重新入队，方便 UI 观察重新处理结果
uv run quantagent-source-event-replay replay --raw-event-id rawevt_xxx --clear-routed
```

注意：

- 回放不会删除 `raw_events` / `raw_event_captures`，只会重新发布 `source.event.captured`。
- `--clear-routed` 只删除所选 RawEvent 对应的 `event_intake_routed_events` read model，用于回测重新观察；不要在生产环境随意使用。
- worker 必须运行：`uv run quantagent-worker`。如果 worker 没启动，回放消息只会留在 Kafka 等待消费。
- worker 默认最多同时处理 10 条 Kafka 消息，可通过 `EVENT_BUS_KAFKA_CONSUMER_CONCURRENCY` 调整；legacy batch 消息内的文章并发可通过 `WORKER_ARTICLE_CONCURRENCY` 调整。Kafka offset 只提交每个 partition 上连续成功的 offset，避免并发乱序完成造成消息丢失。

### AI intake 模型兼容要求

当前 `industry.analysis.requested -> event.routed` 的单次 AI intake 走受控结构化输出路径。用于该链路的 provider / model 需要同时满足：

- 兼容 OpenAI-style chat completions
- 支持 `response_format={\"type\":\"json_object\"}` 或等价的强制 JSON object 输出
- 能稳定返回单个 JSON object，而不是 markdown、自然语言前后缀或 tool call

这意味着：

- `/models` 页面里的“检测连接”只验证基础连通性，不等价于验证该模型可用于 AI intake
- 某些兼容网关虽然能通过 smoke prompt，但如果不支持结构化 JSON 输出，运行到 worker intake 阶段仍会失败或退回 review

### Compose 默认启动建议

如果你想尽量少记命令，推荐直接用 Compose 默认配置：

```bash
cp .env.example .env
docker compose up -d db
docker compose --profile migration run --rm migrate
docker compose up --build api
```

如果要跑完整跨进程链路，再加上 Kafka、scheduler 和 worker：

```bash
docker compose up -d kafka
docker compose up --build scheduler worker
```

说明：

- Compose 内部默认使用 `COMPOSE_DATABASE_URL=postgresql+psycopg://quantagent:quantagent@db:5432/quantagent`
- 宿主机直跑默认使用 `DATABASE_URL=postgresql+psycopg://quantagent:quantagent@127.0.0.1:15432/quantagent`
- 两套地址不再混用

## 半导体 RSS 主链路现状

截至 2026-06-03，这条主链路已经具备以下可运行结论：

- `uv run api` 只启动 HTTP 服务，不会自动抓 RSS，也不会自动消费 `source.event.captured`
- `scheduler` 需要单独启动，负责抓 RSS、写 `SchedulerRun`、发布 `source.event.captured`
- `worker` 需要单独启动，负责消费 `source.event.captured`、尝试 Readability、再发布 `industry.analysis.requested`；后续 AI intake 发布 `event.routed` 后会写入 `event_intake_routed_events`，供 `/runtime` 展示真实 Router output
- `EVENT_BUS_BACKEND=memory` 只能证明单进程内链路；默认跨进程运行必须使用 Kafka
- `uv run quantagent-source-bindings install-semiconductor-defaults` 负责把行业包模板安装成真实 DB `SourceBinding`；只提交模板文件不会自动让 scheduler 开始抓取

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
| `https://www.digitimes.com/rss/daily.xml` | 供应链与制造链信号更强，条目量更大，作为 optional expansion |
| `https://www.electronicsweekly.com/feed/` | 电子行业媒体 feed，适合补充欧洲产业动态 |
| `https://www.servethehome.com/feed/` | 数据中心与服务器硬件 feed，适合补充 AI 基础设施信号 |
| `https://news.google.com/rss/search?q=semiconductor%20OR%20memory%20OR%20HBM&hl=en-US&gl=US&ceid=US:en` | Google News 聚合源，覆盖广但噪音和重复更高 |
| `https://news.google.com/rss/search?q=NVIDIA%20OR%20Micron%20OR%20SK%20hynix%20OR%20TSMC&hl=en-US&gl=US&ceid=US:en` | Google News 厂商舆情聚合源 |
| `https://export.arxiv.org/rss/cs.AR` | 研究向 RSS，适合补充技术前沿 |

当前不建议直接放进默认模板的候选：

| Feed | 原因 |
| --- | --- |
| `https://export.arxiv.org/rss/cs.LG` | 当前环境是真 RSS，但响应体约 1.9MiB，超过插件 schema 上限 |
| `https://www.anandtech.com/rss/` | 当前环境返回 HTML 页面，不是真 feed |
| `https://investor.amd.com/rss/news-releases.xml` | 当前环境 TLS 握手不稳定 |
