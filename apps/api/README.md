# QuantAgent API

## 运行

### 启动

```bash
cd apps/api
uv sync
APP_ENV=development uv run api
```

### Docker

从仓库根目录构建并启动 API：

```bash
docker compose up --build api
```

只启动本地数据库：

```bash
docker compose up -d db
```

`db` 容器内端口为 `5432`，宿主机默认绑定 `127.0.0.1:15432`，可通过 `.env` 中的 `DB_HOST` 和 `DB_PORT` 调整。

Compose 中的 API 容器通过 `API_DATABASE_URL` 连接 `db:5432`；宿主机本地工具通过 `DATABASE_URL` 连接 `localhost:15432`。

如果修改了 `POSTGRES_DB`、`POSTGRES_USER` 或 `POSTGRES_PASSWORD`，需要同步调整 `API_DATABASE_URL` 和 `MIGRATION_DATABASE_URL`。

需要执行 Alembic 迁移时，从仓库根目录运行：

```bash
docker compose --profile migration run --rm migrate
```

## API v1 route skeleton

### 基本约定

- 默认会返回统一的 `code/data/msg/error` 响应信封。
- 请求与错误响应都会携带 `X-Request-ID`。
- `APP_ENV=production` 时不会加载 `/api/v1/debug/*` 路由。
- 标准 API v1 routes 放在 `src/quantagent/api/routers/`。
- request/response DTO 放在 `src/quantagent/api/schemas/`。
- sample 或可替换的数据边界放在 `src/quantagent/api/providers/`。
- 标准 routes 统一通过 `quantagent.api.routers.register.register_api_v1_routes` 注册，不要继续在 `main.py` 零散 `include_router(...)`。
- route 应显式声明 FastAPI `response_model=ApiResponse[T]` 和 OpenAPI `tags`。
- `GET /api/v1/version` 是最小非业务示例：它只展示 DTO、provider、envelope 和 OpenAPI 契约，不代表 runtime、plugin、approval、Agent、tool invocation、WebSocket、executor、live trading 或业务 endpoint family 已完成。
- `/api/v1/ready` 继续是数据库 readiness probe；不要把 sample provider 和请求级 DB session dependency 混在一起。
- 本包当前不生成 static OpenAPI artifact、generated client、TypeScript types 或 Zod schema。

### Auth 基础闭环

- 当前 API 初版采用本地单用户 Cookie Session 鉴权，不实现注册、RBAC、多用户、多租户、OAuth 或 SSO。
- public 路由白名单仅包含 `GET /api/v1/health`、`GET /api/v1/ready`、`GET /api/v1/version`；业务 API 默认 protected。
- 登录入口为 `POST /api/v1/auth/login`，请求体使用本地管理员口令；成功后仅通过 HttpOnly cookie 建立 session。
- 登出入口为 `POST /api/v1/auth/logout`，必须同时具备有效 session 和 `X-CSRF-Token`。
- 当前用户快照入口为 `GET /api/v1/me`，返回 `actor_id`、`actor_type`、`capabilities` 和非敏感 `csrf_token`，不返回 session、cookie、secret、口令或 hash。
- Cookie 默认 `HttpOnly` 且 `SameSite=Lax`；`APP_ENV=production` 下要求 `Secure=true`。
- `AUTH_ENABLED=false` 仅允许 `APP_ENV=development`；此时依赖会返回 `local_dev` actor，避免下游审计上下文为空。
- Cookie Session 写操作通过 `X-CSRF-Token` header 做 CSRF 校验；login 豁免，logout 和受保护写操作不豁免。

### Auth 环境变量

- `AUTH_ENABLED`：是否启用鉴权，默认 `true`。
- `AUTH_ADMIN_PASSWORD`：本地管理员登录口令；`APP_ENV=development`、`APP_ENV=test` 和 `APP_ENV=local` 可使用默认值，`staging` 和 `production` 必须显式提供。
- `AUTH_SESSION_SECRET`：session 签名 secret；`APP_ENV=development`、`APP_ENV=test` 和 `APP_ENV=local` 可使用默认值，`staging` 和 `production` 必须显式提供。
- `AUTH_COOKIE_NAME`：session cookie 名称，默认 `quantagent_session`。
- `AUTH_COOKIE_SECURE`：是否对 session cookie 启用 `Secure`；production 默认强制安全值。
- `AUTH_COOKIE_SAME_SITE`：cookie same-site 策略，默认 `lax`。
- `AUTH_SESSION_LIFETIME_SECONDS`：session 生命周期，默认 `43200`。
- `AUTH_CSRF_HEADER_NAME`：CSRF header 名称，默认 `X-CSRF-Token`。

注意：仓库本地 Docker compose 仅代表本地运行默认值，不等同 production 安全部署；生产环境需要显式设置 `APP_ENV=production` 及对应 auth 配置。

## 服务器部署方案初版

本节是一版面向单台 Linux 服务器的部署方案，便于先把前端、后端和数据库跑通。当前仓库已有后端 Dockerfile 和 Compose 入口，前端是 Vite 静态构建产物，推荐由 Nginx 托管并反向代理 API。

### 推荐拓扑

```text
Browser
  |
  | https://example.com
  v
Nginx
  |-- /                 -> apps/web/dist 静态文件
  |-- /api/v1/*         -> 127.0.0.1:8000
  |-- /openapi.json     -> 127.0.0.1:8000/openapi.json，可按需关闭公网访问
  |
Docker Compose
  |-- api               -> FastAPI，容器内 8000
  |-- db                -> PostgreSQL 17
  |-- migrate           -> 一次性 Alembic migration profile
```

推荐前后端同域部署，API 使用 `/api/v1` 相对路径。这样可以复用 HttpOnly Cookie Session，减少跨域、SameSite 和 CSRF 配置复杂度。

### 服务器前置条件

- 一台 Linux 服务器，开放 `80` 和 `443`；`8000`、`15432` 建议只绑定本机或内网。
- 已安装 `git`、Docker、Docker Compose plugin、Nginx。
- 用于构建前端的 Bun 版本与根目录 `package.json` 中的 `packageManager` 保持一致；当前为 `bun@1.3.14`。
- 已准备域名和 TLS 证书。证书可以由平台、Certbot 或云厂商证书服务管理。

### 目录规划

示例目录如下，可按服务器规范调整：

```bash
/opt/quantagent
├── current/            # Git 工作副本
├── env/                # 生产环境变量文件，不提交 Git
│   └── api.env
├── web/                # 前端静态产物
│   └── dist/
└── runtime/            # API runtime 数据、日志或缓存
```

### 服务器首次操作

首次部署建议按以下顺序准备服务器。示例以 Ubuntu/Debian 系为准，其他发行版按等价命令处理：

```bash
sudo apt-get update
sudo apt-get install -y git nginx ca-certificates curl rsync
```

安装 Docker 和 Docker Compose plugin 后，确认命令可用：

```bash
docker --version
docker compose version
```

创建部署目录和运行时目录：

```bash
sudo mkdir -p /opt/quantagent/{current,env,web/dist,runtime,backups/postgres}
sudo chown -R "$USER":"$USER" /opt/quantagent
chmod 700 /opt/quantagent/env
chmod 700 /opt/quantagent/backups
```

准备代码和本地生产配置：

```bash
git clone <repo-url> /opt/quantagent/current
cd /opt/quantagent/current
cp /opt/quantagent/env/api.env .env
chmod 600 .env
```

注意：上面的 `api.env` 需要先按“后端环境变量”章节创建；如果还没有准备好生产变量，先不要启动服务。

如果服务器使用独立部署用户，建议只给该用户 Docker、代码目录、运行时目录和备份目录权限；Nginx reload 可通过受限 sudoers 规则放行，不建议长期使用 root 执行发布脚本。

### 需要部署的文件

当前方案分为“仓库源码”“服务器本地配置”和“构建产物”三类。

需要从仓库部署到服务器：

- 根目录 `Dockerfile`：构建 API runtime 镜像。
- 根目录 `docker-compose.yml`：启动 `api`、`db`、`migrate`。
- 根目录 `pyproject.toml`、`uv.lock`：后端依赖锁定。
- `apps/api/`：FastAPI 应用源码和包定义。
- `packages/core/`：共享配置、数据库和 Alembic migration。
- 根目录 `package.json`、`apps/web/package.json`、`apps/web/bun.lock`：前端 workspace 和依赖锁定。
- `apps/web/`：前端源码，用于构建静态产物。

只应保留在服务器本地，不提交 Git：

- `/opt/quantagent/env/api.env`：生产环境变量和 secret。
- `/opt/quantagent/current/.env`：如沿用默认 Compose，可由 `api.env` 复制或软链生成。
- `/opt/quantagent/current/docker-compose.prod.yml`：服务器本地生产覆盖文件，确认不含 secret 后才考虑入库。
- `/etc/nginx/sites-available/quantagent` 或等价 Nginx 配置。
- TLS 证书、数据库备份、运行时缓存和日志。

构建后需要发布的产物：

- API Docker image：由服务器本地 `docker compose build api` 构建，或后续由 CI 构建并推送到镜像仓库。
- 前端静态产物：`apps/web/dist/` 同步到 `/opt/quantagent/web/dist/`。
- 数据库迁移结果：通过 `migrate` 服务写入 PostgreSQL，不是文件拷贝。

不需要部署或不应部署到生产：

- `__pycache__`、`.pyc`、测试缓存、前端测试报告、Playwright 浏览器缓存。
- 本地 `.env.example` 中的弱口令原值。
- `runtime/` 中的本地私有数据，除非明确是生产需要恢复的数据。
- 未经审核的 OpenSpec draft、临时脚本或个人调试文件。

### 后端环境变量

生产环境不要直接使用 `.env.example` 里的弱口令。建议在服务器创建 `/opt/quantagent/env/api.env`：

```bash
APP_ENV=production
LOG_LEVEL=INFO

POSTGRES_DB=quantagent
POSTGRES_USER=quantagent
POSTGRES_PASSWORD=<replace-with-strong-password>

API_DATABASE_URL=postgresql+psycopg://quantagent:<replace-with-strong-password>@db:5432/quantagent
MIGRATION_DATABASE_URL=postgresql+psycopg://quantagent:<replace-with-strong-password>@db:5432/quantagent

API_BIND_HOST=127.0.0.1
API_PORT=8000
API_RUNTIME_DIR=/app/runtime
DB_HOST=127.0.0.1
DB_PORT=15432

AUTH_ENABLED=true
AUTH_ADMIN_PASSWORD=<replace-with-strong-admin-password>
AUTH_SESSION_SECRET=<replace-with-long-random-secret>
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAME_SITE=lax
```

生成 `AUTH_SESSION_SECRET` 的示例：

```bash
openssl rand -hex 32
```

如果服务器上使用当前 `docker-compose.yml`，它默认从仓库根目录 `.env` 读取变量。可以把生产 env 文件复制或软链为仓库根目录 `.env`：

```bash
cp /opt/quantagent/env/api.env /opt/quantagent/current/.env
chmod 600 /opt/quantagent/current/.env
```

### 后端构建与启动

生产环境建议优先使用下一节的 `docker-compose.prod.yml` 覆盖文件，并统一通过 `--env-file /opt/quantagent/env/api.env` 启动，避免误用本地默认值。

如果只是快速验证当前根目录 `docker-compose.yml`，可以从仓库根目录执行：

```bash
cd /opt/quantagent/current
docker compose build api
docker compose up -d db
docker compose --profile migration run --rm migrate
docker compose up -d api
```

检查容器状态：

```bash
docker compose ps
docker compose logs --tail=100 api
```

后端健康检查：

```bash
curl -i http://127.0.0.1:8000/api/v1/health
curl -i http://127.0.0.1:8000/api/v1/ready
```

`/api/v1/health` 只验证 API 进程存活；`/api/v1/ready` 会验证数据库 readiness。生产环境下 debug route 不应出现在 OpenAPI 中。

### 生产 Compose 覆盖示例

当前根目录 `docker-compose.yml` 偏本地开发。生产环境建议额外维护一个服务器本地的 `docker-compose.prod.yml`，避免把生产专属策略提交到默认 Compose：

```yaml
services:
  api:
    restart: unless-stopped
    env_file:
      - /opt/quantagent/env/api.env
    environment:
      APP_ENV: production
      HOST: 0.0.0.0
      PORT: 8000
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - /opt/quantagent/runtime:/app/runtime
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  migrate:
    env_file:
      - /opt/quantagent/env/api.env
    environment:
      APP_ENV: production

  db:
    restart: unless-stopped
    env_file:
      - /opt/quantagent/env/api.env
    ports:
      - "127.0.0.1:${DB_PORT:-15432}:5432"
```

使用覆盖文件启动：

```bash
cd /opt/quantagent/current
set -a
. /opt/quantagent/env/api.env
set +a
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env build api
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env up -d db
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env --profile migration run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env up -d api
```

如果后续要把 `docker-compose.prod.yml` 纳入仓库，需要先确认它不包含真实 secret，并在 PR 中说明生产部署约束。

### 前端环境变量

前端当前通过 Vite 环境变量构建，变量会写入构建产物。推荐同域部署：

```bash
VITE_API_BASE_URL=/api/v1
VITE_WEBSOCKET_URL=
VITE_AUTH_ENABLED=true
```

如必须使用独立 API 域名，需要先确认后端 CORS、Cookie `SameSite=None; Secure`、CSRF header 和反向代理 header 策略；当前推荐先不要走跨域部署。

### 前端构建与发布

从仓库根目录执行：

```bash
cd /opt/quantagent/current
bun install --frozen-lockfile
VITE_API_BASE_URL=/api/v1 VITE_AUTH_ENABLED=true bun run --cwd apps/web build
mkdir -p /opt/quantagent/web/dist
rsync -a --delete apps/web/dist/ /opt/quantagent/web/dist/
```

如果需要在构建前做最小验证：

```bash
bun run --cwd apps/web test:unit
bun run --cwd apps/web build
```

### Nginx 示例配置

以下示例使用同域部署，Nginx 托管前端静态文件，并把 `/api/v1` 转发给本机 API 容器发布端口：

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    root /opt/quantagent/web/dist;
    index index.html;

    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000/api/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

启用并验证 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

如果不希望公网暴露 OpenAPI，可删除 `location /openapi.json` 或限制来源 IP。

### 发布流程

一次常规发布可以按以下顺序执行：

1. 拉取新代码：`git fetch --all --prune`，切到目标 tag 或 commit。
2. 加载生产环境：`set -a && . /opt/quantagent/env/api.env && set +a`。
3. 后端：使用 `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env build api` 构建镜像。
4. 数据库：先启动 `db`，备份 PostgreSQL，再运行 `migrate`。
5. 后端：使用同一组 Compose 参数 `up -d api`。
6. 前端：设置 `VITE_*` 变量并运行 `bun run --cwd apps/web build`。
7. 静态资源：`rsync -a --delete apps/web/dist/ /opt/quantagent/web/dist/`。
8. Nginx：`sudo nginx -t && sudo systemctl reload nginx`。
9. 验证：访问 `/api/v1/health`、`/api/v1/ready`、首页和登录流程。

### 发布脚本示例

服务器可以维护一个不提交 Git 的 `/opt/quantagent/deploy.sh`，把重复步骤固化下来。以下脚本默认使用生产 Compose 覆盖文件，并在 migration 前备份数据库：

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/quantagent/current
ENV_FILE=/opt/quantagent/env/api.env
WEB_DIST=/opt/quantagent/web/dist
BACKUP_DIR=/opt/quantagent/backups/postgres
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file $ENV_FILE"
REVISION="${1:-main}"

cd "$APP_DIR"

if [ -n "$(git status --porcelain)" ]; then
  echo "工作树不干净，请先提交、暂存或清理服务器本地改动。" >&2
  exit 1
fi

set -a
. "$ENV_FILE"
set +a

git fetch --all --prune
if git show-ref --verify --quiet "refs/remotes/origin/$REVISION"; then
  git checkout -B "$REVISION" "origin/$REVISION"
else
  git checkout --detach "$REVISION"
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/quantagent-$(date +%Y%m%d-%H%M%S).dump"

$COMPOSE up -d db
$COMPOSE exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$BACKUP_FILE"

$COMPOSE build api
$COMPOSE --profile migration run --rm migrate
$COMPOSE up -d api

bun install --frozen-lockfile
VITE_API_BASE_URL=/api/v1 VITE_AUTH_ENABLED=true bun run --cwd apps/web build

mkdir -p "$WEB_DIST"
rsync -a --delete apps/web/dist/ "$WEB_DIST/"

sudo nginx -t
sudo systemctl reload nginx

curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null
curl -fsS http://127.0.0.1:8000/api/v1/ready >/dev/null
```

使用方式：

```bash
chmod 700 /opt/quantagent/deploy.sh
/opt/quantagent/deploy.sh main
/opt/quantagent/deploy.sh <tag-or-commit>
```

脚本会把远程分支更新到 `origin/<branch>`，传入 tag 或 commit 时使用 detached checkout。正式脚本可以按团队发布习惯拆成分支发布和 tag 发布两个入口。

### 发布后验证清单

```bash
curl -i https://example.com/api/v1/health
curl -i https://example.com/api/v1/ready
curl -I https://example.com/
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env logs --tail=100 api
```

浏览器侧重点检查：

- 首页静态资源是否正常加载。
- 登录是否成功写入 HttpOnly cookie。
- 需要鉴权的接口是否返回预期数据，而不是 401、403 或 CSRF 错误。
- 响应头中是否有 `X-Request-ID`。

### 回滚建议

- 后端镜像回滚：部署前保留上一版 image tag，异常时把 `api` 服务切回上一版镜像并 `docker compose up -d api`。
- 前端回滚：发布前备份 `/opt/quantagent/web/dist`，异常时恢复旧目录并 reload Nginx。
- 数据库迁移回滚需要按迁移内容单独评估；生产执行 migration 前应先备份数据库。

### 数据库备份与恢复

生产执行 migration、升级镜像或调整数据库配置前，应先做数据库备份。使用 Compose 内的 `db` 服务备份：

```bash
cd /opt/quantagent/current
set -a
. /opt/quantagent/env/api.env
set +a
mkdir -p /opt/quantagent/backups/postgres
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  > /opt/quantagent/backups/postgres/quantagent-$(date +%Y%m%d-%H%M%S).dump
```

恢复前先停止 API，避免恢复过程中有新写入：

```bash
cd /opt/quantagent/current
set -a
. /opt/quantagent/env/api.env
set +a
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env stop api
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env exec -T db \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  < /opt/quantagent/backups/postgres/<backup-file>.dump
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file /opt/quantagent/env/api.env up -d api
```

恢复操作会改写数据库内容，执行前需要确认目标备份文件、当前环境和停机窗口。涉及 destructive migration 时，优先在 staging 或临时恢复库验证。

### 日志与运维检查

常用日志入口：

```bash
cd /opt/quantagent/current
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 db
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

常用巡检项：

- `docker compose ps` 中 `api` 和 `db` 应保持运行。
- `/api/v1/health` 和 `/api/v1/ready` 应返回成功响应信封。
- `/opt/quantagent/runtime`、Docker volume 和备份目录磁盘空间不能耗尽。
- Nginx access log 中不应持续出现 502、504、401 或 CSRF 错误。
- PostgreSQL 备份文件需要定期清理或转存到对象存储，避免占满服务器磁盘。

### 后续 CI/CD 演进

当前文档先按“服务器本地构建和发布”描述，适合初版上线和手工验证。后续 CI/CD 建议分三步演进，避免一开始把发布链路做得过重。

第一阶段：CI 只做验证，不自动发布。

- 后端：执行 `cd apps/api && uv run python -m unittest discover -s src/tests`。
- 前端：执行 `bun install --frozen-lockfile`、`bun run --cwd apps/web test:unit`、`bun run --cwd apps/web build`。
- Docker：执行 `docker build --target runtime -t quantagent-api:<sha> .`，验证镜像可构建。
- 产出：CI 只报告结果，不接触生产服务器和生产 secret。

第二阶段：CI 构建不可变产物，服务器拉取部署。

- CI 构建并推送 API 镜像到镜像仓库，tag 使用 commit SHA 或 release tag。
- CI 构建前端 `dist`，作为 artifact 上传，或打包成独立静态资源包。
- 服务器发布脚本接收 image tag 和前端 artifact，只负责备份、迁移、切换版本和健康检查。
- 生产环境变量仍只保存在服务器或部署平台 secret store，不进入 CI 日志和 artifact。

第三阶段：受控 CD。

- main 分支只部署 staging；production 通过 tag、GitHub Environment approval 或手工审批触发。
- 发布前自动备份数据库，发布后自动访问 `/api/v1/health`、`/api/v1/ready` 和前端首页。
- 失败时自动停止后续步骤，并保留上一版前端目录和上一版 API image tag。
- migration 仍需要谨慎处理；破坏性 migration 不建议完全自动化，应要求人工确认和备份校验。

后续如要落地 GitHub Actions，可以优先拆成两个 workflow：

- `ci.yml`：PR 和 main push 触发，只跑测试、构建和 Docker build。
- `release.yml`：tag 或手工触发，构建镜像、上传前端 artifact，并通过 SSH 或部署平台触发服务器发布脚本。

不建议在第一版 CI/CD 中直接把 `api.env`、数据库连接串或 SSH 私钥写入仓库；应使用 GitHub Secrets、部署平台 secret store 或服务器本地配置文件。

### 生产安全注意事项

- 不要把 `.env`、生产口令、session secret 或数据库备份提交到 Git。
- `APP_ENV=production` 时必须显式设置 `AUTH_ADMIN_PASSWORD` 和 `AUTH_SESSION_SECRET`。
- `API_BIND_HOST` 建议保持 `127.0.0.1`，由 Nginx 对公网提供 HTTPS。
- PostgreSQL 端口不建议暴露公网；当前 Compose 默认绑定 `127.0.0.1:15432`。
- 生产环境建议配置服务器防火墙，只开放 `22`、`80`、`443` 和必要的运维入口。
- 如果后续引入 WebSocket、外部行情源、插件 runtime 或多用户权限，需要同步更新部署文档、环境变量和反向代理配置。

### 新增 route 流程

新增一个 API v1 route 的最小流程：

1. 在 `schemas/` 中定义 DTO，保持 API 契约独立于 ORM model。
2. 在 `providers/` 中放 sample data 或替换点，不引入数据库访问、外部服务调用、credentials、runtime 状态或核心领域逻辑。
3. 在 `routers/` 中定义 route，返回 `ApiResponse[T]`，并显式声明 `response_model` 和 `tags`。
4. 通过 `register_api_v1_routes` 接入标准 router 列表。
5. 在 `src/tests/` 中补运行时 route 测试和 `/openapi.json` 契约测试。

### 最小验证

新增或调整 API v1 route 后，最小本地验证入口：

```bash
cd apps/api && uv run python -m unittest discover -s src/tests
```
