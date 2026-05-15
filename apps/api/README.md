# QuantAgent API

## 启动

```bash
cd apps/api
uv sync
APP_ENV=development uv run api
```

## 说明

- 默认会返回统一的 `code/data/msg/error` 响应信封。
- 请求与错误响应都会携带 `X-Request-ID`。
- `APP_ENV=production` 时不会加载 `/api/v1/debug/*` 路由。
