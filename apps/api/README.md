# QuantAgent API

## 启动

```bash
cd apps/api
uv sync
APP_ENV=development uv run api
```

## Docker

从仓库根目录构建并启动 API：

```bash
docker compose up --build api
```

只启动本地数据库：

```bash
docker compose up -d db
```

`db` 容器内端口为 `5432`，宿主机默认映射到 `15432`，可通过 `.env` 中的 `DB_PORT` 调整。

## 说明

- 默认会返回统一的 `code/data/msg/error` 响应信封。
- 请求与错误响应都会携带 `X-Request-ID`。
- `APP_ENV=production` 时不会加载 `/api/v1/debug/*` 路由。
