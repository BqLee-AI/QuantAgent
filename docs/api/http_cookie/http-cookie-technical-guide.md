# HTTP Cookie 技术实现原理

## 文档定位

本文面向需要理解 Cookie 协议、浏览器行为和 QuantAgent API Cookie Session 实现的后端、前端和审查人员。它描述 HTTP Cookie 的通用机制，也说明当前 `apps/api` 中本地单用户 Cookie Session 的落地方式。

本文不是认证系统长期扩展方案；多用户、RBAC、OAuth、SSO、跨域前后端部署和第三方 Cookie 兼容策略需要通过 OpenSpec 另行收束。

相关真源：

- API 当前认证实现：`apps/api/src/quantagent/api/auth.py`
- 认证路由：`apps/api/src/quantagent/api/routers/auth.py`
- API 配置：`apps/api/src/quantagent/api/config/settings.py`
- 前端路由说明：`docs/api/auth/auth_frontend_routes.md`
- API 本地说明：`apps/api/README.md`

## Cookie 是什么

HTTP 本身是无状态协议。Cookie 是浏览器维护的一小段站点状态，由服务端通过响应头写入，后续浏览器在符合匹配条件的请求中自动带回服务端。

典型写入响应：

```http
HTTP/1.1 200 OK
Set-Cookie: quantagent_session=<session-value>; Max-Age=43200; Path=/; HttpOnly; SameSite=Lax
```

后续匹配请求：

```http
GET /api/v1/me HTTP/1.1
Host: localhost:8000
Cookie: quantagent_session=<session-value>
```

关键点：

- `Set-Cookie` 是响应头，只有浏览器或 HTTP client 的 cookie jar 会保存。
- `Cookie` 是请求头，浏览器按域名、路径、安全属性、SameSite 和过期时间自动决定是否附带。
- `HttpOnly` Cookie 不能被前端 JavaScript 读取，但仍会随请求发送。
- Cookie 不是加密存储。不要把 secret、口令、私有策略或敏感明文直接放进 Cookie。

## 浏览器保存模型

浏览器保存 Cookie 时至少会记录以下维度：

| 维度 | 作用 |
| --- | --- |
| name | Cookie 名称，例如 `quantagent_session` |
| value | Cookie 值，服务端定义格式 |
| domain | 允许发送到哪些 host；未设置时默认 host-only |
| path | 允许发送到哪些 URL path；当前项目使用 `/` |
| expires / max-age | 绝对过期时间或相对生命周期 |
| secure | 仅允许 HTTPS 请求携带，`localhost` 开发环境有浏览器特例 |
| httpOnly | 禁止 `document.cookie` 读取或写入 |
| sameSite | 限制跨站请求是否携带 |
| partitioned | CHIPS 分区 Cookie，用于第三方上下文隔离 |

浏览器发送 Cookie 时不会参考前端代码能否读取 Cookie，而是参考请求目标和 Cookie 属性。因此 `HttpOnly` 可以防止脚本读取 session 原文，但不能单独防止 CSRF。

## 生命周期

### 签发

服务端在登录成功或需要刷新状态时返回 `Set-Cookie`。浏览器校验属性后保存。

QuantAgent 当前登录入口：

```text
POST /api/v1/auth/login
```

当前实现会：

- 校验本地管理员口令。
- 生成包含 actor、过期时间、capability 和 CSRF token 的 session payload。
- 使用 `AUTH_SESSION_SECRET` 对规范化 payload 做 HMAC 签名。
- 将 `base64url(payload).signature` 写入 HttpOnly Cookie。
- 在响应体 `data.csrf_token` 返回非敏感 CSRF token 给前端写操作使用。

开发环境存在一个显式 bypass：仅当 `APP_ENV=development` 且 `AUTH_ENABLED=false` 时，登录不会校验密码，也不会签发有效 session；后端会清除已有 session cookie，并返回固定的 `local_dev` actor 和开发态 CSRF token。该模式只用于本地开发，不是生产降级策略。

### 携带

浏览器在后续请求中自动携带匹配 Cookie。前端不需要，也不能读取 HttpOnly session 原文。

同源请求通常会自动携带 Cookie。跨 origin 请求需要前端显式设置 `credentials: "include"` 或 axios `withCredentials: true`，并要求服务端 CORS 配置允许 credentials。

### 校验

服务端从请求 Cookie 中取 session 值，然后执行：

1. 拆分 payload 和 signature。
2. base64url 解码 payload。
3. 用 `AUTH_SESSION_SECRET` 重新计算 HMAC。
4. 用常量时间比较校验签名。
5. 校验 actor 类型、过期时间、capabilities 集合和 CSRF token。
6. 构造脱敏 `CurrentActor`，供 route dependency、审计和后续 Policy Gate 使用。

签名只能证明 Cookie 未被客户端篡改，不能隐藏 payload 内容。当前 payload 不应放入 secret。

当前 session 是签名 token，不是加密 token。任何能拿到 Cookie 原文的人都可能解码 payload，因此 payload 只允许放脱敏 actor、过期时间、capability 集合和 CSRF token 这类可校验上下文。

### 过期

Cookie 有两层过期：

- 浏览器层：`Max-Age` 或 `Expires` 到期后浏览器不再发送。
- 服务端层：session payload 的 `exp` 到期后，即使浏览器仍发送也会被拒绝。

QuantAgent 当前 `AUTH_SESSION_LIFETIME_SECONDS` 默认 `43200` 秒，最小值由配置校验限制为 `300` 秒。

### 清除

服务端通过同名、同 path、同安全属性的删除响应让浏览器清理 Cookie。当前登出入口：

```text
POST /api/v1/auth/logout
```

登出必须具备有效 session 和有效 `X-CSRF-Token`，成功后通过 `Set-Cookie` 清除 session。

## Cookie 属性详解

### Domain

`Domain` 控制 Cookie 可发送到哪些 host。未设置 `Domain` 时，Cookie 通常是 host-only，只发送给设置它的 host。

生产建议默认不设置 `Domain`，除非确实需要多个子域共享登录态。共享子域会扩大泄露和错误发送范围。

### Path

`Path` 控制 URL 路径匹配范围。当前项目使用 `/`，表示 API host 下所有路径都可携带 session。

`Path` 不是安全边界。同一 host 下其他路径通常仍能通过请求行为影响 Cookie，因此不能用 `Path` 替代权限设计。

### Max-Age 和 Expires

`Max-Age` 是相对秒数，优先级通常高于 `Expires`。当前项目使用 `Max-Age=AUTH_SESSION_LIFETIME_SECONDS`。

只设置浏览器过期时间不够，服务端 session payload 也必须有 `exp`，避免客户端或中间层异常保留 Cookie 后仍被接受。

### HttpOnly

`HttpOnly` 禁止 JavaScript 通过 `document.cookie` 读取或写入 Cookie。它主要降低 XSS 直接窃取 session 的风险。

当前项目没有暴露 `AUTH_COOKIE_HTTP_ONLY` 配置项；`set_session_cookie(...)` 和 `clear_session_cookie(...)` 固定使用 `httponly=True`。如果未来要引入开关，必须先通过 OpenSpec 说明风险和兼容策略。

### Secure

`Secure` 表示 Cookie 只应通过 HTTPS 发送。生产环境必须开启，否则 session 可能在非 TLS 链路中泄露。

当前项目规则：

- 未显式配置时，`AUTH_COOKIE_SECURE` 根据 `APP_ENV` 推导。
- `APP_ENV=production` 时必须为 true。
- 本地 development 可以为 false，方便 `http://localhost` 调试。

### SameSite

`SameSite` 限制跨站请求携带 Cookie 的行为：

| 值 | 行为 |
| --- | --- |
| `Strict` | 只有同站请求携带，最严格，可能影响外部跳转后的体验 |
| `Lax` | 同站请求携带；部分顶层安全导航可携带；常用默认值 |
| `None` | 跨站请求也可携带；现代浏览器要求同时设置 `Secure` |

当前项目默认 `SameSite=Lax`。如果未来前端和 API 进入真正跨站部署，例如不同站点而非仅不同端口，需要重新评估 CORS、`SameSite=None; Secure`、CSRF 和部署域名。

### Partitioned

`Partitioned` 是 CHIPS 相关属性，用于第三方上下文下按顶层站点隔离 Cookie，并要求 `Secure`。当前 QuantAgent 不依赖第三方 iframe 或嵌入式第三方上下文，因此不使用 `Partitioned`。

## Same-Origin、Same-Site 和 CORS

Cookie 的发送规则容易混淆三组概念：

| 概念 | 判断维度 | 常见用途 |
| --- | --- | --- |
| origin | scheme + host + port | 浏览器同源策略、CORS、Fetch credentials |
| site | scheme + registrable domain | `SameSite` Cookie 判断 |
| host | 具体域名或 IP | Cookie host-only/domain 匹配 |

例子：

- `http://localhost:5173` 到 `http://localhost:8000`：不同 origin，因为端口不同。
- `https://app.example.com` 到 `https://api.example.com`：不同 origin，但通常是 same-site。
- `https://app.example.com` 到 `https://api.other.com`：不同 origin 且 cross-site。

CORS 只控制浏览器是否允许前端读取响应，不自动放宽 Cookie 规则。当前 `apps/api` 尚未暴露通用 CORS 配置；如果前端和 API 不同 origin，必须先在 API 层补齐明确 allowlist，而不是只改前端 credentials。

跨 origin 使用 Cookie 时，前端和后端都要配合：

- 前端 fetch/axios 设置 credentials。
- 后端 CORS 不能使用 `Access-Control-Allow-Origin: *` 搭配 credentials。
- 后端需要返回明确 origin 和 `Access-Control-Allow-Credentials: true`。
- Cookie 自身仍要满足 `SameSite`、`Secure`、domain/path 等规则。

## 安全风险和防护

### Session 篡改

风险：客户端修改 Cookie payload，提升 actor 或 capability。

当前防护：session payload 使用 HMAC 签名，服务端使用 `hmac.compare_digest` 校验签名和 CSRF token。

### Session 泄露

风险：网络窃听、XSS、日志、错误响应或代理记录泄露 Cookie。

当前防护：

- 生产强制 `Secure`。
- 强制 `HttpOnly`。
- 错误响应不回显 session、secret 或 cookie 原文。
- 认证依赖只返回脱敏 actor。

仍需注意：

- 不要在日志、toast、错误面板或测试快照中打印 `Set-Cookie` 原文。
- 前端不要尝试把 Cookie 复制到 localStorage。

### CSRF

风险：攻击站点诱导浏览器向 QuantAgent 发起带 Cookie 的写请求。

`HttpOnly` 不能阻止 CSRF，因为浏览器仍会自动带 Cookie。

当前防护：

- Cookie 默认 `SameSite=Lax`。
- 写操作必须提交 `X-CSRF-Token`。
- CSRF token 只通过登录响应和 `/api/v1/me` 的 JSON data 给前端。
- logout 和受保护写操作不豁免 CSRF，login 豁免。

### XSS

风险：攻击脚本不能读取 HttpOnly session，但可以代表用户发起请求，或读取页面内保存的 CSRF token。

Cookie Session 不能替代前端 XSS 防护。前端仍需避免危险 HTML 注入，谨慎处理第三方内容和插件输出。

## QuantAgent 当前实现摘要

相关文件：

- `src/quantagent/api/auth.py`
- `src/quantagent/api/routers/auth.py`
- `src/quantagent/api/config/settings.py`
- `src/tests/test_app.py`

当前约定：

| 项 | 当前值或行为 |
| --- | --- |
| Cookie 名称 | `AUTH_COOKIE_NAME`，默认 `quantagent_session` |
| Cookie path | `/` |
| HttpOnly | 强制 true |
| Secure | production 强制 true，development 可关闭 |
| SameSite | 默认 `lax`，允许 `lax` / `strict` / `none` |
| Session 格式 | `base64url(canonical_json_payload).hmac_sha256_signature` |
| Session 内容 | `sub`、`type`、`exp`、`csrf`、`capabilities` |
| 登录 | `POST /api/v1/auth/login` |
| 登出 | `POST /api/v1/auth/logout`，要求 CSRF |
| 当前用户 | `GET /api/v1/me` |
| 写操作 CSRF header | `AUTH_CSRF_HEADER_NAME`，默认 `X-CSRF-Token` |
| development bypass | 仅 `APP_ENV=development` 允许 `AUTH_ENABLED=false`；返回 `local_dev`，不签发有效 session |

## 调试清单

Cookie 未写入时检查：

- 登录响应是否包含 `Set-Cookie`。
- 是否处于 `AUTH_ENABLED=false` 的 development bypass；该模式登录会清理 Cookie 而不是签发 session。
- Cookie 是否被浏览器因 `SameSite=None` 但缺少 `Secure` 拒绝。
- HTTPS/HTTP 与 `Secure` 是否匹配。
- domain、host、path 是否匹配当前访问地址。

Cookie 未发送时检查：

- 请求 URL 是否匹配 Cookie host/path。
- 前端跨 origin 请求是否设置 axios `withCredentials: true` 或 fetch `credentials: "include"`。
- 服务端 CORS 是否允许 credentials 和明确 origin。
- 当前 API 是否已经实际接入 CORS 中间件；未接入时浏览器会先在 CORS 层拦截。
- 当前请求是否被 `SameSite` 规则拦截。
- Cookie 是否已过期或被 logout 清除。

服务端拒绝 session 时检查：

- session payload 是否过期。
- `AUTH_SESSION_SECRET` 是否变化。
- Cookie 是否来自旧环境或旧 host。
- capability 是否超出当前 `ALL_CAPABILITIES`。
- 错误响应是否包含一致的 `X-Request-ID`，便于定位日志。

## 参考资料

- MDN: HTTP cookies, `https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies`
- MDN: Set-Cookie header, `https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie`
- MDN: Fetch API credentials, `https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch`
- IETF RFC 6265: HTTP State Management Mechanism, `https://www.rfc-editor.org/rfc/rfc6265`
