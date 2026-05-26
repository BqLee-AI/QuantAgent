# QuantAgent API

## 本地开发

### 依赖安装

```bash
cd apps/api
uv sync
```

### 启动 API

```bash
APP_ENV=development uv run api
```

API dotenv 文件按从低到高读取：仓库根目录 `.env`、当前工作目录 `.env`、`apps/api/.env`、`apps/api/.env.local`、`apps/api/.env.<APP_ENV>`、`apps/api/.env.<APP_ENV>.local`。重复变量允许存在，API 目录下的文件会覆盖根 `.env`；真实进程环境变量仍是最高优先级，适合 CI/CD secret、部署 secret 和临时强制覆盖。

`APP_ENV` 先从真实环境变量读取；如果没有，再由根 `.env`、`apps/api/.env`、`apps/api/.env.local` 这几个基础层决定，用于选择对应的 `apps/api/.env.<APP_ENV>` 和 `.local` 文件。协作模板使用 `.example` 后缀，真实 `.env*` 文件不要提交。

API 默认监听 `127.0.0.1:8000`。`APP_ENV=development` 或 `APP_ENV=local` 下，`uv run api` 会默认启用热更新；`staging`/`production` 等非本地环境保持单进程启动。鉴权默认开启（`AUTH_ENABLED=true`）；development、test、local 环境下口令可使用代码中的弱默认值，也可显式设置 `AUTH_ENABLED=false` 完全关闭鉴权；staging 和 production 必须提供安全口令和 session secret。

### 测试

```bash
cd apps/api && uv run python -m unittest discover -s src
```

Alpaca wallet API E2E validation 也落在 `apps/api/src/tests/`，只做测试链路验证，不新增任何 Alpaca route 或 runtime adapter：

- 默认离线 E2E：使用 `apps/api/src/tests/alpaca_wallet_api_e2e_support.py` 中抽出的最小 Alpaca-shaped mapping helper，与 `WalletService.ingest_paper_execution()`、既有 `/api/v1/wallet/**` 只读 endpoints 组成受控读回链路。
- 可选外部 smoke：只有同时满足 `QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE=1`、`QUANTAGENT_ALPACA_PAPER_SMOKE=1`、paper credentials 与 `https://paper-api.alpaca.markets` URL guard 时才运行。
- 外部 smoke 只读取 Alpaca paper account、positions、orders；本地 wallet state 使用 `acct_alpaca_e2e_redacted`、`order_redacted_*`、`client_redacted_*`、`activity_redacted_*` 等脱敏 identifier，不提交 paper order。

窄验证命令：

```bash
cd apps/api && uv run python -m unittest src/tests/test_alpaca_wallet_api_e2e.py
```

可选外部 smoke：

```bash
cd apps/api && \
QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE=1 \
QUANTAGENT_ALPACA_PAPER_SMOKE=1 \
APCA_API_KEY_ID=redacted \
APCA_API_SECRET_KEY=redacted \
uv run python -m unittest src/tests/test_alpaca_wallet_api_e2e.py
```

## Docker 部署

### 首次启动（完整流程）

从仓库根目录执行：

```bash
cp .env.example .env          # 首次配置，按需修改变量
cp apps/api/.env.example apps/api/.env
# Docker Compose 中将 apps/api/.env 的 DATABASE_URL 改为 db:5432，并将 RUNTIME_DIR 改为 /app/runtime。
docker compose up -d db
docker compose --profile migration run --rm migrate
docker compose up --build api
```

### 只启动数据库

```bash
docker compose up -d db
```

`db` 容器内端口为 `5432`，宿主机默认绑定 `127.0.0.1:15432`，可通过 `.env` 中的 `DB_HOST` 和 `DB_PORT` 调整。

Compose 不再把根 `.env` 中的 API 应用配置硬注入为 API 进程环境变量。API 容器同样通过 `apps/api/.env` 或选中的 `apps/api/.env.<APP_ENV>` 读取 `DATABASE_URL`、`RUNTIME_DIR`、`LOG_LEVEL`、`AUTH_*` 等配置；容器侧数据库 URL 应使用 `db:5432`，宿主机直跑可使用 `localhost:15432`。

Compose 不注入 `HOST` 或 `PORT`，避免宿主机 shell 变量覆盖 API 配置；容器内监听地址由镜像启动命令固定为 `0.0.0.0:8000`。根 `.env` 中的 `API_BIND_HOST`、`API_PORT` 只控制宿主机发布地址和端口，不改变容器内监听端口。

为了保留 dotenv 优先级，Compose 不为 API 服务提供 `APP_ENV`、`DATABASE_URL`、`RUNTIME_DIR`、`LOG_LEVEL` 回退注入。首次启动前应创建 `apps/api/.env`，并把容器侧 `DATABASE_URL` 配成 `db:5432`、`RUNTIME_DIR` 配成 `/app/runtime`。

`./apps/api:/app/apps/api` 挂载主要用于让容器内可见 API dotenv 覆盖文件；`./runtime:/app/runtime` 挂载前请确认宿主机 `runtime/` 目录已存在，避免 Docker 创建 root-owned 空目录影响后续写入。

如果修改了 `POSTGRES_DB`、`POSTGRES_USER` 或 `POSTGRES_PASSWORD`，需要同步调整 `apps/api/.env*` 中给 API 容器使用的 `DATABASE_URL` 和根 `.env` 中给迁移服务使用的 `MIGRATION_DATABASE_URL`。

### 数据库迁移

执行数据库迁移，从仓库根目录运行：

```bash
docker compose --profile migration run --rm migrate
```

本地直跑时使用 `packages/core` 提供的独立 CLI：

```bash
uv run quantagent-db upgrade
uv run quantagent-db current
uv run quantagent-db check
```

API 启动流程不自动执行迁移；API 只负责创建数据库连接并通过 `/api/v1/ready` 暴露 readiness probe。

如果依赖仓库根目录 `.env` 中的 `DATABASE_URL`，请从仓库根目录运行这些 `uv run` 命令。若在 `packages/core` 或其他子目录执行，需要显式提供 `DATABASE_URL`，或改用 `uv run quantagent-db --database-url <DATABASE_URL> upgrade` 这类带参数的调用。服务器或容器中如果已经把 `quantagent-db` 安装进虚拟环境或镜像 `PATH`，命令默认会从当前目录及其祖先目录尝试定位 `packages/core/alembic.ini` 和 `packages/core/alembic/`；如果部署目录不保留这类仓库结构，需要通过 `QUANTAGENT_CORE_MIGRATION_ROOT=/path/to/packages/core` 显式指定迁移目录。

### 健康检查

```bash
docker compose ps
docker compose logs --tail=100 api
curl -i http://127.0.0.1:8000/api/v1/health
curl -i http://127.0.0.1:8000/api/v1/ready
```

`/api/v1/health` 只验证 API 进程存活；`/api/v1/ready` 验证数据库可达。

### 生产注意事项

仓库本地 Compose 默认值仅用于本地开发，不等同生产安全部署。生产环境启动前，至少在 API dotenv、真实进程环境变量、CI/deployment secret 或未来 Secret Manager 中提供以下安全值：

- `APP_ENV=production`
- 数据库账号、密码和 `DATABASE_URL`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_SESSION_SECRET`（建议用 `openssl rand -hex 32` 生成）

`APP_ENV=production` 时 API 会强制验证这些配置，启动时若检测到弱默认值（`AUTH_ADMIN_PASSWORD=12345678` 或 `AUTH_SESSION_SECRET=dev-session-secret-change-me`）、短口令、短 session secret 或配置缺失，会直接报错退出。

## API v1 route skeleton

### 基本约定

- 默认会返回统一的 `code/data/msg/error` 响应信封。
- 请求与错误响应都会携带 `X-Request-ID`。
- `APP_ENV=production` 时不会加载 `/api/v1/debug/*` 路由。
- HTTP 传输层基础能力放在 `src/quantagent/api/http/`。
- API 私有 Cookie Session 鉴权放在 `src/quantagent/api/auth/`。
- 标准 API v1 routes 放在 `src/quantagent/api/routers/v1/`。
- request/response DTO 放在 `src/quantagent/api/schemas/`。
- sample 或可替换的数据边界放在 `src/quantagent/api/providers/`。
- 标准 routes 统一通过 `quantagent.api.routers.v1.register.register_api_v1_routes` 注册，不要继续在 `main.py` 零散 `include_router(...)`。
- route 应显式声明 FastAPI `response_model=ApiResponse[T]` 和 OpenAPI `tags`。
- `GET /api/v1/version` 是最小非业务示例：它只展示 DTO、provider、envelope 和 OpenAPI 契约，不代表 runtime、plugin、approval、Agent、tool invocation、WebSocket、broker、live trading 或业务 endpoint family 已完成。
- `/api/v1/ready` 继续是数据库 readiness probe；不要把 sample provider 和请求级 DB session dependency 混在一起。
- 本包当前不生成 static OpenAPI artifact、generated client、TypeScript types 或 Zod schema。

### Auth 基础闭环

- 当前 API 初版采用本地单用户 Cookie Session 鉴权，不实现注册、RBAC、多用户、多租户、OAuth 或 SSO。
- public 路由白名单仅包含 `GET /api/v1/health`、`GET /api/v1/ready`、`GET /api/v1/version` 和 `POST /api/v1/auth/login`；其余 API v1 routes 默认 protected。
- 登录入口为 `POST /api/v1/auth/login`，请求体使用本地管理员口令；成功后仅通过 HttpOnly cookie 建立 v2 session。
- 显式续期入口为 `POST /api/v1/auth/refresh`，必须同时具备有效 session 和 `X-CSRF-Token`；只有接近 idle timeout 时才会回写新的 cookie。
- 登出入口为 `POST /api/v1/auth/logout`，必须同时具备有效 session 和 `X-CSRF-Token`。
- 当前用户快照入口为 `GET /api/v1/me`，返回 `actor_id`、`actor_type`、`capabilities` 和非敏感 `csrf_token`，不返回 session、cookie、secret、口令或 hash。
- `/api/v1/me` 不再作为主要 refresh 入口；仅在识别旧 v1 cookie 时执行一次兼容升级。
- 非 production 的 `/api/v1/debug/*` 仍会注册到 OpenAPI，但默认按 protected route 处理，不加入 public allowlist。
- Cookie 默认 `HttpOnly` 且 `SameSite=Lax`；`APP_ENV=production` 下要求 `Secure=true`。
- `AUTH_ENABLED=false` 仅允许 `APP_ENV=development`、`APP_ENV=test` 或 `APP_ENV=local`；此时依赖会返回 `local_dev` actor，避免下游审计上下文为空。
- Cookie Session 写操作通过 `X-CSRF-Token` header 做 CSRF 校验；login 豁免，refresh/logout 和受保护写操作不豁免。
- `quantagent.api.routers.v1.register` 中的 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 与 registration helper 是 public/protected 真源；README、OpenAPI 或 route-level ad hoc dependency 只用于说明与补充，不替代该边界。

### Portfolio Wallet API V1

- `GET /api/v1/wallet/accounts/{account_id}`
- `GET /api/v1/wallet/accounts/{account_id}/cash-balances`
- `GET /api/v1/wallet/accounts/{account_id}/positions`
- `GET /api/v1/wallet/accounts/{account_id}/ledger-entries?limit=<positive-int>`
- `GET /api/v1/wallet/accounts/{account_id}/paper-orders`
- `GET /api/v1/wallet/accounts/{account_id}/paper-executions`

以上 route 都是 `protected`、`read-only`、`paper-only` 的 API 薄封装。

- 只负责鉴权、DTO 映射、统一 envelope、错误映射和调用 `WalletService`
- 不支持账户创建、现金调整、paper order 写入、paper execution 写入
- 不暴露 `WalletFacts` 前端查询 endpoint
- 不暗示 live broker sync、真实下单、撤单、改单、换汇或资金划转能力

### API/Auth 环境变量

- `APP_ENV`：选择 API 运行环境，并决定是否追加读取 `apps/api/.env.<APP_ENV>` 和 `apps/api/.env.<APP_ENV>.local`。
- `DATABASE_URL`：API 数据库连接串；容器内应指向 `db:5432`，宿主机直跑通常指向 `localhost:15432`。
- `RUNTIME_DIR`：API 运行时目录，容器内通常为 `/app/runtime`，宿主机直跑通常为 `./runtime`。
- `LOG_LEVEL`：应用日志级别，例如 `DEBUG`、`INFO`、`WARNING`、`ERROR`。
- `API_HOST`：直跑 API 时的监听地址，默认 `127.0.0.1`；兼容读取历史变量名 `HOST`。Compose 中不注入该变量，容器内由启动命令监听 `0.0.0.0`。
- `API_PORT`：直跑 API 时的监听端口，默认 `8000`；兼容读取历史变量名 `PORT`。在根目录 Compose 中，该变量只表示宿主机发布端口，容器内监听端口固定为 `8000`。
- `API_V1_PREFIX`：API v1 路由前缀，默认 `/api/v1`。
- `AUTH_ENABLED`：是否启用鉴权，默认 `true`。
- `AUTH_ADMIN_PASSWORD`：本地管理员登录口令；`APP_ENV=development`、`APP_ENV=test` 和 `APP_ENV=local` 默认值为 `12345678`，`staging` 和 `production` 必须显式提供。
- `AUTH_SESSION_SECRET`：session 签名 secret；`APP_ENV=development`、`APP_ENV=test` 和 `APP_ENV=local` 可使用默认值，`staging` 和 `production` 必须显式提供。
- `AUTH_COOKIE_NAME`：session cookie 名称，默认 `quantagent_session`。
- `AUTH_COOKIE_SECURE`：是否对 session cookie 启用 `Secure`；production 默认强制安全值。
- `AUTH_COOKIE_SAME_SITE`：cookie same-site 策略，默认 `lax`。
- `AUTH_SESSION_LIFETIME_SECONDS`：idle timeout 窗口，默认 `43200`。
- `AUTH_SESSION_ABSOLUTE_LIFETIME_SECONDS`：absolute timeout 上限，默认 `86400`。
- `AUTH_SESSION_REFRESH_THRESHOLD_SECONDS`：显式 refresh 触发重签的剩余 idle 阈值，默认 `1800`。
- `AUTH_CSRF_HEADER_NAME`：CSRF header 名称，默认 `X-CSRF-Token`。
- `MODEL_CONFIG_ENCRYPTION_KEY`：模型供应商 API key 入库加密主密钥；配置模型 key 前必须设置，值可用 Fernet key 生成命令创建。API 不会返回或记录该值。

### 模型 provider API

- `GET /api/v1/models/providers`：返回多个 OpenAI-compatible provider 的脱敏摘要列表和默认 provider id。
- `POST /api/v1/models/providers`：创建新的 provider；请求可提交 API key，服务端加密入库，响应不回显明文。
- `GET /api/v1/models/providers/{provider_id}`：返回单个 provider 的脱敏详情。
- `PUT /api/v1/models/providers/{provider_id}`：更新 provider 配置；API key 为写入式覆盖字段。
- `POST /api/v1/models/providers/{provider_id}/actions/set-default`：将 provider 设为默认项。
- `POST /api/v1/models/providers/{provider_id}/actions/test-connection`：使用固定 smoke prompt 验证指定 provider，并记录 provider 维度 token usage。
- `GET /api/v1/models/invocations`：返回最近模型调用摘要；支持按 `provider_id` 过滤。

模型 provider 配置属于受保护管理面，不放入 Settings 或插件配置；写接口需要有效 Cookie Session 和 CSRF header。

### 新增 route 流程

新增一个 API v1 route 的最小流程：

1. 在 `schemas/` 中定义 DTO，保持 API 契约独立于 ORM model。
2. 在 `providers/` 中放 sample data 或替换点，不引入数据库访问、外部服务调用、credentials、runtime 状态或核心领域逻辑。
3. 在 `routers/` 中定义 route，返回 `ApiResponse[T]`，并显式声明 `response_model` 和 `tags`。
4. 标准 API v1 router 变更应更新 `STANDARD_API_V1_ROUTER_REGISTRATIONS`；额外测试 router 可使用 `register_api_v1_protected_router` 接入统一 registration boundary。
5. 在 `src/tests/` 中补运行时 route 测试和 `/openapi.json` 契约测试。

### 最小验证

新增或调整 API v1 route 后，最小本地验证入口：

```bash
cd apps/api && uv run python -m unittest discover -s src
```
