# 前端 Cookie Session 接入指南

## 文档定位

本文面向 QuantAgent 前端开发者，说明如何接入当前 API 的本地单用户 Cookie Session 鉴权。它只覆盖前端调用、状态管理、CSRF 和调试要点，不重复解释完整 Cookie 协议细节。

当前 API 初版使用 HttpOnly Cookie Session：

- 前端不能读取 session cookie 原文。
- 登录成功后浏览器自动保存 Cookie。
- 前端保存的是 `/api/v1/me` 或登录响应返回的 actor 快照和 `csrf_token`。
- 受保护写操作必须带 `X-CSRF-Token`。

相关文档：

- 接口字段速查：`docs/api/auth/auth_frontend_routes.md`
- Cookie 协议与后端实现细节：`docs/api/http_cookie/http-cookie-technical-guide.md`
- 当前前端 API client：`apps/web/src/shared/api/client.ts`

## 接口速览

所有接口默认位于 `/api/v1` 前缀下，并返回 `code/data/msg/error` envelope。

| 场景 | Method | Path | 说明 |
| --- | --- | --- | --- |
| 登录 | `POST` | `/api/v1/auth/login` | 提交本地管理员口令，成功后服务端写 HttpOnly Cookie |
| 当前用户 | `GET` | `/api/v1/me` | 用 Cookie 换取脱敏 actor 快照和 CSRF token |
| 登出 | `POST` | `/api/v1/auth/logout` | 需要有效 Cookie 和 `X-CSRF-Token`，成功后清 Cookie |

登录成功响应 data 示例：

```json
{
  "actor_id": "local_admin",
  "actor_type": "local_single_user",
  "capabilities": [
    "runtime.inspect",
    "plugin.configure"
  ],
  "csrf_token": "<csrf-token>"
}
```

前端不要期望响应体里出现 session、cookie 名称、cookie 值、secret、口令或 hash。

## 前端状态模型

建议前端只维护两类状态：

| 状态 | 来源 | 是否持久化到 localStorage |
| --- | --- | --- |
| 登录态是否已确认 | `/api/v1/me` 成功或失败 | 否 |
| actor 快照和 `csrf_token` | login 或 `/api/v1/me` 响应 | 否 |

不要保存：

- session cookie 原文。前端读不到，也不应该读。
- 管理员口令。
- `AUTH_SESSION_SECRET`。
- `Set-Cookie` header。
- 长期可复用的 CSRF token 副本。
- bearer access token。当前 Cookie Session 不需要前端从 localStorage 注入 `Authorization`。

刷新页面后，通过 `/api/v1/me` 重新 bootstrap。浏览器会自动带上 HttpOnly Cookie，前端只需要重新拿 actor 和 CSRF token。

## API Client 接入

当前 `apps/web/src/shared/api/client.ts` 使用 axios，并默认 `withCredentials: true`。这与 Cookie Session 匹配：浏览器负责保存和发送 HttpOnly Cookie，前端 client 只处理响应 envelope、actor 快照和 CSRF header。

如果在局部代码中直接使用 fetch，保持同样规则：

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type ApiEnvelope<T> = {
  code: number;
  data: T | null;
  msg: string;
  error: {
    code?: string;
    request_id?: string;
    trace_id?: string;
    details?: unknown;
    retryable?: boolean;
  } | null;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  const body = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || body.code !== 0 || body.error) {
    throw new ApiError(body.msg, response.status, body.error);
  }
  if (body.data === null) {
    throw new ApiError("Empty response data", response.status, body.error);
  }
  return body.data;
}
```

`credentials: "include"` 和 axios `withCredentials: true` 的含义是允许跨 origin 请求携带 Cookie。它不会让前端读到 HttpOnly Cookie，也不能绕过服务端 CORS 或 Cookie `SameSite` 限制。

注意：当前 `apps/api` 尚未暴露通用 CORS 配置。如果前端通过不同 origin 调用 API，后端也需要明确加入 CORS allowlist 和 credentials 支持；不要只在前端设置 credentials。

## 登录流程

```ts
type AuthenticatedActor = {
  actor_id: string;
  actor_type: "local_single_user";
  capabilities: string[];
  csrf_token: string;
};

export async function login(password: string): Promise<AuthenticatedActor> {
  return request<AuthenticatedActor>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}
```

登录成功后：

1. 浏览器自动保存服务端返回的 HttpOnly Cookie。
2. 前端把响应中的 actor 和 `csrf_token` 放进内存状态或 TanStack Query cache。
3. 跳转到受保护页面。
4. 不要从 `document.cookie` 读取 session；读不到是预期行为。

开发环境如果 API 使用 `APP_ENV=development` 且 `AUTH_ENABLED=false`：

- 登录请求不会校验密码。
- 后端会清理已有 session cookie，不会签发有效 session。
- login 和 `/api/v1/me` 都返回 `local_dev` actor 以及开发态 CSRF token。
- 前端仍应走相同的 actor/CSRF 状态路径，不要为 bypass 模式单独绕过写操作 header。

登录失败时：

- HTTP status 通常为 401。
- 使用 envelope 的 `msg` 展示错误。
- 可在错误详情里展示 `error.request_id` 方便排查。
- 不要把用户输入的口令写入日志、URL、toast debug detail 或错误上报。

## 启动时恢复登录态

应用启动时请求 `/api/v1/me`：

```ts
export async function getCurrentActor(): Promise<AuthenticatedActor> {
  return request<AuthenticatedActor>("/api/v1/me");
}
```

推荐行为：

- 成功：写入 actor 和 `csrf_token`，进入应用。
- 401：视为未登录，清空前端内存状态，进入登录页。
- 其他错误：展示可重试错误状态，保留 `request_id`。

不要通过“本地是否有某个 cookie”判断登录态，因为 HttpOnly Cookie 不可读，且 Cookie 存在也可能已过期或服务端签名已失效。

## 写操作和 CSRF

所有受保护写操作都要带 `X-CSRF-Token`。当前 login 豁免，logout 和其他受保护写操作不豁免。

```ts
let csrfToken: string | null = null;

export function setAuthContext(actor: AuthenticatedActor | null): void {
  csrfToken = actor?.csrf_token ?? null;
}

export async function postWithCsrf<T>(path: string, payload?: unknown): Promise<T> {
  if (!csrfToken) {
    throw new ApiError("Missing CSRF token", 401, null);
  }

  return request<T>(path, {
    method: "POST",
    headers: {
      "X-CSRF-Token": csrfToken,
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
}
```

CSRF token 处理规则：

- 从 login 或 `/api/v1/me` 响应获取。
- 存在内存或 query cache 中。
- 页面刷新后通过 `/api/v1/me` 重新获取。
- 不写入 localStorage、URL、埋点或错误日志。
- 收到 403 时可以重新调用 `/api/v1/me` 刷新上下文；仍失败则回到登录页或显示权限错误。
- 只把 CSRF token 加到受保护写操作上，不需要给普通 GET 请求加。

## 登出流程

```ts
type LogoutResponse = {
  cleared: boolean;
};

export async function logout(): Promise<LogoutResponse> {
  return postWithCsrf<LogoutResponse>("/api/v1/auth/logout");
}
```

登出成功后：

1. 服务端清除 Cookie。
2. 前端清空 actor、csrfToken、相关 query cache。
3. 跳转登录页。

登出返回 401 或 403 时，也应清空本地前端状态。服务端可能已经不接受当前 session，或者当前 CSRF token 已失效；继续保留前端状态会造成 UI 和真实登录态不一致。

## TanStack Query 建议

建议用 `me` query 作为认证 bootstrap：

```ts
export const authQueryKey = ["auth", "me"] as const;

export function useMeQuery() {
  return useQuery({
    queryKey: authQueryKey,
    queryFn: getCurrentActor,
    retry: false,
  });
}
```

登录 mutation 成功后：

- `queryClient.setQueryData(authQueryKey, actor)`。
- 调用 `setAuthContext(actor)`。
- invalidate 依赖 actor capability 的页面数据。

登出 mutation settled 后：

- `setAuthContext(null)`。
- `queryClient.removeQueries()` 或按 auth 相关范围清理。避免清掉与公开页面或静态配置相关、无需认证的缓存，除非当前应用还没有这类缓存分层。
- 跳转登录页。

## Capability 使用

后端返回 `capabilities` 是前端控制可见操作的依据之一，但不是安全边界。前端可以用它隐藏按钮、禁用入口或提示权限不足；真正的权限判断仍由后端 dependency、Policy Gate 和审计完成。

示例：

```ts
function can(actor: AuthenticatedActor | null, capability: string): boolean {
  return Boolean(actor?.capabilities.includes(capability));
}
```

前端不要因为按钮隐藏就省略后端错误处理。任何 mutation 仍可能返回 401、403 或业务错误码。

## 本地开发注意事项

当前 API 默认：

- Cookie 名称：`quantagent_session`。
- `SameSite=Lax`。
- development 可使用非 Secure Cookie。
- production 强制 Secure Cookie。
- development/test/local 会为 `AUTH_ADMIN_PASSWORD` 和 `AUTH_SESSION_SECRET` 提供弱默认值；staging 和 production 必须显式配置。

如果前端 dev server 和 API 不同 origin，例如：

```text
http://localhost:5173 -> http://localhost:8000
```

需要确认：

- API client 使用 axios `withCredentials: true`；如果直接使用 fetch，则使用 `credentials: "include"`。
- 后端已经实际接入 CORS 中间件，并明确允许前端 origin 和 credentials。
- 不要使用 `Access-Control-Allow-Origin: *` 搭配 credentials。
- 浏览器 Network 面板中 login 响应存在 `Set-Cookie`。
- Application/Storage 面板中 Cookie 被保存到 API host。

如果未来部署为：

```text
https://app.example.com -> https://api.example.com
```

这通常是 cross-origin 但 same-site。仍需要 CORS credentials，但 `SameSite=Lax` 在多数同站 API 请求中不会按第三方站点处理。

如果未来部署为真正 cross-site：

```text
https://app.example.com -> https://api.other.com
```

需要后端、部署和安全设计一起调整，通常涉及 `SameSite=None; Secure`、更严格 CSRF、防嵌入策略和 CORS allowlist；不要只在前端改 credentials。

## 常见问题

### `document.cookie` 看不到 `quantagent_session`

这是预期行为。session Cookie 是 `HttpOnly`，前端 JavaScript 不能读取。

### 登录成功但 `/api/v1/me` 返回 401

检查：

- login 响应是否有 `Set-Cookie`。
- API 是否处于 development bypass；该模式会清 Cookie 而不是签发 session，但 `/api/v1/me` 应直接返回 `local_dev`。
- 浏览器是否拒绝保存 Cookie。
- `/api/v1/me` 请求是否设置 axios `withCredentials: true` 或 fetch `credentials: "include"`。
- 请求 host、scheme、port 是否和 Cookie 保存位置匹配。
- API 服务是否重启并更换了 `AUTH_SESSION_SECRET`。

### 写操作返回 403

检查：

- 是否带了 `X-CSRF-Token`。
- token 是否来自当前 login 或 `/api/v1/me`。
- 登出后是否仍使用旧 token。
- 是否误把 CSRF token 存成空字符串或旧 query cache。

### 生产环境登录后没有 Cookie

检查：

- 站点是否使用 HTTPS。
- `APP_ENV=production` 下 `AUTH_COOKIE_SECURE=true`。
- 反向代理是否保留 `Set-Cookie`。
- API 域名和前端请求域名是否和 Cookie domain/path 匹配。

### 跨域请求报 CORS

Cookie credentials 需要前后端同时配置。前端 axios `withCredentials: true` 或 fetch `credentials: "include"` 只是一半；后端也必须返回明确的 allowed origin 和 `Access-Control-Allow-Credentials: true`。

## 前端实现检查清单

- API client 全局设置 axios `withCredentials: true`；如果直接使用 fetch，则设置 `credentials: "include"`。
- 登录成功后只保存 actor 和 `csrf_token`，不处理 Cookie 原文。
- 应用启动通过 `/api/v1/me` 恢复登录态。
- 所有受保护写操作带 `X-CSRF-Token`。
- 401 清空登录态并进入登录页。
- 403 区分 CSRF 缺失、权限不足和业务禁止，展示 `request_id`。
- 登出无论成功、401 或 403，都清空前端 auth cache。
- 不把 password、session、Cookie、CSRF token 写入日志、URL、localStorage 或错误上报。
