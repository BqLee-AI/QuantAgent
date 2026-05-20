# Design: API v1 public allowlist 与默认 protected 注册边界

## 背景

`apps/api` 已经具备 API v1 route skeleton、统一 `code/data/msg/error` envelope、request id、debug route production 隐藏、数据库 readiness、Cookie Session auth、CurrentActor、capability guard 和 CSRF guard。

当前缺口不是 auth primitive，而是 route 注册边界：后续业务 router 仍可能通过裸 `include_router` 或未声明 dependency 的方式进入 API v1，导致“业务 API 默认 protected”只停留在约定层。

本设计将 API v1 route 注册收敛为可审核控制面。实现阶段应让 public/protected 分类成为代码结构和测试都能检查的事实。

## 关键决策

### API v1 public allowlist 显式维护

public allowlist 固定为：

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/version`
- `POST /api/v1/auth/login`

这些 route 允许匿名访问。新增 public route 必须有 OpenSpec、issue 或设计文档依据，并同步测试。

`GET`、只读或非敏感描述本身不是 public 理由。业务 route 默认 protected。

### 注册边界优先使用 helper，而不是 path middleware

首选实现是在 `register_api_v1_routes` 或相邻模块中提供专门 registration helper，要求每个 API v1 router 被声明为 public 或 protected。protected router 在注册时统一注入 `get_current_actor` 或等价 session dependency。

不把 path middleware 作为首选方案，原因是 middleware 会把鉴权策略绑定到 method/path 字符串，容易与 FastAPI dependency override、OpenAPI dependency 表达、route-level capability/CSRF guard 和 debug route 环境注册产生耦合。

实现可以从当前 `register_api_v1_routes` 起步，但不能继续让新业务 router 通过裸 `app.include_router(...)` 绕过分类边界后仍被视为合格。

registration boundary 是本 change 的权限真源。README、OpenAPI、测试 helper 或 route docstring 都只能作为说明或证据，不能覆盖 registration boundary 的 public/protected 分类。

禁止的替代路径：

- 在每个业务 route 上临时手写 `Depends(get_current_actor)`，但不建立统一 public/protected 分类。
- 让业务 router 直接调用 `app.include_router(...)` 后依赖人工 code review 记住补 dependency。
- 把 OpenAPI security 标注当成 runtime auth 保护。

### 默认 protected 只提供 session 前提

默认 protected 的职责是确保请求有有效 session 并解析出 `CurrentActor`。

它不替代：

- `require_capability(...)`
- `require_csrf`
- 后续 Policy Gate
- 后续 audit persistence

需要更细权限的 route 仍必须显式声明 capability guard。cookie-session 写操作仍必须显式声明 CSRF guard。

### Auth routes 分类

`POST /api/v1/auth/login` 是 public，因为登录前没有既有 session。

`POST /api/v1/auth/logout` 不是 public。logout 应先满足默认 protected session 前提，再执行 `require_csrf`。如果实现导致 session 解析重复，可以接受轻微重复或在同一 helper 内复用依赖结果；不得为了避免重复而把 logout 放入 public allowlist。

`GET /api/v1/me` 是 protected，用于返回当前 actor、capability snapshot 和非敏感 `csrf_token`。

### Debug routes 分类

debug routes 只在非 production 注册，并且 production OpenAPI 不得暴露 debug paths。

非 production 下 debug routes 不扩展 public allowlist，默认按 protected route 注册。`APP_ENV=development` 且 `AUTH_ENABLED=false` 时，按 #87 已定义的 development bypass actor 通过 protected dependency，这保留本地调试便利性，同时不把 debug 语义扩大为匿名 public。

### OpenAPI security scheme

本 change 的硬门槛是 runtime 强约束与测试。OpenAPI 可在实现阶段补充 cookie auth security scheme，但只有在不扩大生成链路、不破坏当前 `ApiResponse[T]` schema 测试且成本低时才一并处理。

如果未补 security scheme，PR 说明需要明确本轮依赖 runtime tests 和 registration tests 作为强约束，OpenAPI security scheme 留作后续增强。

## 控制流

API app 启动注册：

```text
create_app
  -> register_api_v1_routes(app, settings)
  -> register public routers without session dependency
  -> register protected routers with default session dependency
  -> if non-production: register debug router as protected
```

匿名访问 public route：

```text
request
  -> request id middleware
  -> public route handler
  -> ApiResponse[T]
```

匿名访问 protected route：

```text
request
  -> request id middleware
  -> default protected session dependency
  -> UnauthorizedError
  -> 401 envelope with request_id
```

受保护写操作：

```text
request
  -> default protected session dependency
  -> route-level require_csrf
  -> optional route-level require_capability
  -> handler
```

## 测试策略

实现阶段需要测试一个未显式添加 auth dependency 的 API v1 test router，证明它通过 protected registration 后匿名访问仍返回 401。该测试 router 应只存在测试 app 或测试构造路径中，不能变成业务 endpoint。

registration tests 应覆盖两个层次：

- public allowlist 声明与实际匿名可访问 route 一致。
- protected registration 能保护没有 route-level auth dependency 的 router。

测试至少覆盖：

- public allowlist anonymous success。
- `POST /api/v1/auth/login` anonymous success。
- 未列入 public allowlist 的 API v1 route anonymous 401。
- 同一 protected route 带有效 session success。
- `POST /api/v1/auth/logout` anonymous 401。
- logout 带 session 但缺失或错误 CSRF token 被拒绝。
- capability guard 缺 capability 403。
- 非 production debug route 不作为 public route；production OpenAPI excludes debug-only paths。
- 401/403 envelope 中 `error.request_id` 与 `X-Request-ID` 一致。

不要求测试通过字符串扫描证明所有未来 router 都已分类；但实现 PR 必须让新增 router 的注册入口足够集中，使 review 能看出它选择了 public 还是 protected。

## 取舍

- 不采用全局 path middleware 作为首选，换取 FastAPI dependency 语义、测试 override 和 OpenAPI 表达更清晰。
- 不把 OpenAPI security scheme 作为本轮硬门槛，避免为了文档标注扩大 contracts/generation 范围。
- 不将 debug route 放入 public allowlist，避免非 production 共享环境形成匿名诊断面。
- 不把 CSRF/capability 合并进默认 protected，避免 route-level 风险语义丢失。

## 收口边界

本 change 完成后，后续业务 API 的最低要求是通过统一 registration boundary 注册，并默认获得 session guard。任何新增 public route 都必须显式修改 allowlist、OpenSpec 或对应设计依据，并补测试。
