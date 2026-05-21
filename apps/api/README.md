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

API 默认监听 `127.0.0.1:8000`。鉴权默认开启（`AUTH_ENABLED=true`）；development 环境下口令使用 `.env.example` 中预设的弱默认值，也可显式设置 `AUTH_ENABLED=false` 完全关闭鉴权（此选项仅 `APP_ENV=development` 允许）。

### 测试

```bash
cd apps/api && uv run python -m unittest discover -s src/tests
```

## Docker 部署

### 首次启动（完整流程）

从仓库根目录执行：

```bash
cp .env.example .env          # 首次配置，按需修改变量
docker compose up -d db
docker compose --profile migration run --rm migrate
docker compose up --build api
```

### 只启动数据库

```bash
docker compose up -d db
```

`db` 容器内端口为 `5432`，宿主机默认绑定 `127.0.0.1:15432`，可通过 `.env` 中的 `DB_HOST` 和 `DB_PORT` 调整。

Compose 中的 API 容器通过 `API_DATABASE_URL` 连接 `db:5432`；宿主机本地工具通过 `DATABASE_URL` 连接 `localhost:15432`。

如果修改了 `POSTGRES_DB`、`POSTGRES_USER` 或 `POSTGRES_PASSWORD`，需要同步调整 `API_DATABASE_URL` 和 `MIGRATION_DATABASE_URL`。

### 数据库迁移

执行 Alembic 迁移，从仓库根目录运行：

```bash
docker compose --profile migration run --rm migrate
```

### 健康检查

```bash
docker compose ps
docker compose logs --tail=100 api
curl -i http://127.0.0.1:8000/api/v1/health
curl -i http://127.0.0.1:8000/api/v1/ready
```

`/api/v1/health` 只验证 API 进程存活；`/api/v1/ready` 验证数据库可达。

### 生产注意事项

仓库本地 Compose 默认值仅用于本地开发，不等同生产安全部署。生产环境启动前，至少在 `.env` 中替换以下变量为安全值：

- `APP_ENV=production`
- `POSTGRES_PASSWORD`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_SESSION_SECRET`（建议用 `openssl rand -hex 32` 生成）

`APP_ENV=production` 时 API 会强制验证这些配置，启动时若检测到弱默认值（`AUTH_ADMIN_PASSWORD=dev-admin-password` 或 `AUTH_SESSION_SECRET=dev-session-secret-change-me`）或配置缺失，会直接报错退出。

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
- public 路由白名单仅包含 `GET /api/v1/health`、`GET /api/v1/ready`、`GET /api/v1/version` 和 `POST /api/v1/auth/login`；其余 API v1 routes 默认 protected。
- 登录入口为 `POST /api/v1/auth/login`，请求体使用本地管理员口令；成功后仅通过 HttpOnly cookie 建立 session。
- 登出入口为 `POST /api/v1/auth/logout`，必须同时具备有效 session 和 `X-CSRF-Token`。
- 当前用户快照入口为 `GET /api/v1/me`，返回 `actor_id`、`actor_type`、`capabilities` 和非敏感 `csrf_token`，不返回 session、cookie、secret、口令或 hash。
- 非 production 的 `/api/v1/debug/*` 仍会注册到 OpenAPI，但默认按 protected route 处理，不加入 public allowlist。
- `GET /api/v1/me` 在 session 模式下会自动续期，并回写新的 HttpOnly cookie 与 `csrf_token`。
- Cookie 默认 `HttpOnly` 且 `SameSite=Lax`；`APP_ENV=production` 下要求 `Secure=true`。
- `AUTH_ENABLED=false` 仅允许 `APP_ENV=development`；此时依赖会返回 `local_dev` actor，避免下游审计上下文为空。
- Cookie Session 写操作通过 `X-CSRF-Token` header 做 CSRF 校验；login 豁免，logout 和受保护写操作不豁免。
- `quantagent.api.routers.register` 中的 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 与 registration helper 是 public/protected 真源；README、OpenAPI 或 route-level ad hoc dependency 只用于说明与补充，不替代该边界。

### Auth 环境变量

- `AUTH_ENABLED`：是否启用鉴权，默认 `true`。
- `AUTH_ADMIN_PASSWORD`：本地管理员登录口令；`APP_ENV=development`、`APP_ENV=test` 和 `APP_ENV=local` 默认值为 `12345678`，`staging` 和 `production` 必须显式提供。
- `AUTH_SESSION_SECRET`：session 签名 secret；`APP_ENV=development`、`APP_ENV=test` 和 `APP_ENV=local` 可使用默认值，`staging` 和 `production` 必须显式提供。
- `AUTH_COOKIE_NAME`：session cookie 名称，默认 `quantagent_session`。
- `AUTH_COOKIE_SECURE`：是否对 session cookie 启用 `Secure`；production 默认强制安全值。
- `AUTH_COOKIE_SAME_SITE`：cookie same-site 策略，默认 `lax`。
- `AUTH_SESSION_LIFETIME_SECONDS`：session 生命周期，默认 `43200`。
- `AUTH_CSRF_HEADER_NAME`：CSRF header 名称，默认 `X-CSRF-Token`。

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
cd apps/api && uv run python -m unittest discover -s src/tests
```
