# QuantAgent Auth API 前端路由说明

本文只整理前端需要直接对接的认证接口，不包含运维探针、调试路由或未落地能力。

## 基本信息

- Base Path: `/api/v1`
- 响应格式统一为 `code/data/msg/error`
- 登录态通过 `HttpOnly` Cookie 维护，前端无法直接读取 session 原文
- 依赖 Cookie 的受保护写操作需要额外携带 `X-CSRF-Token`
- 浏览器请求需要带上 credentials，确保 Cookie 能随请求发送

## 统一响应格式

成功响应示例：

```json
{
  "code": 0,
  "data": {},
  "msg": "ok",
  "error": null
}
```

错误响应示例：

```json
{
  "code": 40100,
  "data": null,
  "msg": "Unauthorized",
  "error": {
    "code": "UNAUTHORIZED",
    "request_id": "req-123",
    "trace_id": null,
    "details": {},
    "retryable": false
  }
}
```

## 路由总览

| 方法 | 路径 | 是否公开 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/login` | 是 | 本地管理员登录 |
| POST | `/auth/logout` | 否 | 登出，需要 CSRF |
| GET | `/me` | 否 | 当前登录用户信息 |

当前实现是本地单用户认证模型。正常鉴权启用时 actor 固定为 `local_admin`；仅在 `APP_ENV=development` 且 `AUTH_ENABLED=false` 时，接口返回开发态 actor `local_dev`。

## 详细说明

### 1. `POST /api/v1/auth/login`

用途：本地管理员登录，成功后由后端写入 session cookie。

请求体：

```json
{
  "password": "your-password"
}
```

成功返回 `data`：

```json
{
  "actor_id": "local_admin",
  "actor_type": "local_single_user",
  "capabilities": [
    "approval.amend",
    "approval.approve",
    "executor.dry_run",
    "plugin.configure",
    "plugin.install",
    "runtime.inspect",
    "secret.manage"
  ],
  "csrf_token": "token-string"
}
```

说明：

- 前端必须保存返回的 `csrf_token`
- `set-cookie` 由浏览器自动接收
- 开发环境如果 `AUTH_ENABLED=false`，登录请求不会校验密码，也不会签发有效 session；后端会清理已有 session cookie，并直接返回开发态 actor
- 登录失败返回 `401`，响应体不会回显提交的密码、session secret 或 cookie 原文

### 2. `GET /api/v1/me`

用途：获取当前登录用户快照。

成功返回 `data`：

```json
{
  "actor_id": "local_admin",
  "actor_type": "local_single_user",
  "capabilities": [
    "approval.amend",
    "approval.approve",
    "executor.dry_run",
    "plugin.configure",
    "plugin.install",
    "runtime.inspect",
    "secret.manage"
  ],
  "csrf_token": "token-string"
}
```

前端用途：

- 判断当前是否已登录
- 渲染权限相关 UI
- 取出 `csrf_token` 给后续写操作使用

### 3. `POST /api/v1/auth/logout`

用途：登出当前会话。

请求头：

- `X-CSRF-Token: <csrf_token>`

说明：

- 必须先完成登录
- 缺少或错误的 CSRF token 会返回 `403`
- 缺少、无效或过期 session 会先返回 `401`
- 成功后后端清除 session cookie
- 开发环境如果 `AUTH_ENABLED=false`，登出仍需要使用开发态 `csrf_token`

成功返回：

```json
{
  "cleared": true
}
```

## 鉴权规则

- 这三个接口以外，前端当前不应依赖其他 `apps/api` 路由
- cookie 是 `HttpOnly`，前端 JavaScript 不能读
- 受保护写操作需要 `X-CSRF-Token`，当前认证路由中 `POST /auth/logout` 需要该请求头
- 受保护读操作不需要 CSRF，但需要有效 session cookie
- session cookie 默认名为 `quantagent_session`
- 默认 CSRF header 名为 `X-CSRF-Token`
- session 默认有效期为 43200 秒

## 运行时配置摘要

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `AUTH_ENABLED` | `true` | 是否启用认证；只能在 `APP_ENV=development` 下设为 `false` |
| `AUTH_ADMIN_PASSWORD` | 开发/测试环境为 `dev-admin-password` | 本地管理员登录密码；生产环境必须显式配置 |
| `AUTH_SESSION_SECRET` | 开发/测试环境为 `dev-session-secret-change-me` | session 与 CSRF token 签名密钥；生产环境必须显式配置 |
| `AUTH_COOKIE_NAME` | `quantagent_session` | session cookie 名称 |
| `AUTH_COOKIE_SECURE` | 生产环境默认 `true`，其他环境默认 `false` | 是否只允许 HTTPS 发送 cookie |
| `AUTH_COOKIE_SAME_SITE` | `lax` | 可取 `lax`、`strict`、`none`；`none` 必须配合 secure cookie |
| `AUTH_SESSION_LIFETIME_SECONDS` | `43200` | session 有效期，最小 300 秒 |
| `AUTH_CSRF_HEADER_NAME` | `X-CSRF-Token` | CSRF 请求头名称 |

生产环境会拒绝关闭认证、弱默认密码、弱默认 session secret 和非 secure cookie。

## 前端接入建议

1. 登录成功后，立刻调用一次 `GET /me`，以同步当前用户和权限。
2. 在内存态保存 `csrf_token`，发起写操作时放到请求头。
3. `fetch` 请求设置 `credentials: "include"`；Axios 请求设置 `withCredentials: true`。
4. 遇到 `401` 时，通常意味着登录态失效或未登录。
5. 遇到 `403` 时，通常意味着缺少权限或 CSRF token 不合法。

## 示例请求

登录：

```bash
curl -i \
  -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"dev-admin-password"}'
```

获取当前用户：

```bash
curl -i \
  http://127.0.0.1:8000/api/v1/me \
  --cookie "quantagent_session=..."
```

登出：

```bash
curl -i \
  -X POST http://127.0.0.1:8000/api/v1/auth/logout \
  -H "X-CSRF-Token: your-csrf-token" \
  --cookie "quantagent_session=..."
```
