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
