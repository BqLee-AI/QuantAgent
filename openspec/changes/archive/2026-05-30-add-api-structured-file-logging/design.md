## Context

`apps/api` 当前处于 FastAPI v1 基础骨架阶段，已有统一 `ApiResponse` envelope、异常处理和 `X-Request-ID` 中间件，但日志仍是各模块零散调用 `logging.getLogger("quantagent.api")`。现有实现无法保证所有请求、错误、DB readiness、auth/security 事件都带一致的 `request_id` / `trace_id`，也没有文件落盘、stream 分类、轮转、脱敏、队列写入和高流量磁盘保护策略。

本 change 只处理 API 传输层可观测性。日志数据首版落文件，不写数据库；文件日志用于排查、归档、告警和后续导出，不替代数据库设计中未来 append-only `audit_logs` 业务审计真源。

受影响的现有入口：

- `apps/api/src/quantagent/api/main.py`：应用工厂、生命周期和中间件注册。
- `apps/api/src/quantagent/api/http/middleware.py`：当前 request id 处理。
- `apps/api/src/quantagent/api/http/exceptions.py`：异常 envelope 与未处理异常日志。
- `apps/api/src/quantagent/api/db.py`：数据库初始化、session 和 readiness 失败路径。
- `apps/api/src/quantagent/api/auth/audit.py` 与 auth 相关模块：actor 审计上下文和安全事件。
- `apps/api/README.md`、根 `.env.example`、`apps/api/.env.example` 和 `apps/api/.env.*.example` 多环境模板：日志配置说明。

配置默认值应遵循现有 `Settings` 模型：共享 `RUNTIME_DIR` 仍由 `quantagent-core` 提供，API 专属日志配置留在 `quantagent.api.config.settings.Settings`。`LOG_DIR` 默认解析为 `RUNTIME_DIR / "logs/api"`；只有显式配置 `LOG_DIR` 时才覆盖该默认路径。新增的 `LOG_*` 字段遵循现有 API `Settings` 继承和多环境 dotenv 加载规则，实现者只需在 `Settings` 上声明字段、在对应 `apps/api/.env.*.example` 中补充示例值，不需要修改 dotenv 加载逻辑。

日志模块在初始化时应对 `LOG_DIR` 执行绝对路径解析（例如 `Path.resolve()`），使相对路径 `RUNTIME_DIR` 在启动时就确定实际写入位置，避免因后续进程 cwd 变化导致日志分散到不同目录。

## Goals / Non-Goals

**Goals:**

- 在 `apps/api/src/quantagent/api/observability/` 建立 API 私有日志基础设施。
- 统一 request context，保证 `request_id`、`trace_id` 在响应 header、错误 envelope 和日志记录中一致。
- 输出结构化 JSON Lines 日志，并按 `access`、`app`、`error`、`security`、`audit` stream 分文件落盘。
- 阶段 1 即使用队列化写入，避免普通请求路径直接做文件 IO。
- 支持按小时和大小轮转，文件名包含 service、env、instance_id、pid、stream、小时分片和可选 part 编号。
- 阶段 2 增加关闭文件压缩、按 stream retention、启动补偿清理和磁盘水位保护。
- 明确敏感信息脱敏边界，避免 cookie、token、password、session、数据库连接串、secret 等进入日志。

**Non-Goals:**

- 不引入 OpenTelemetry、APM SDK、collector 或外部日志服务。
- 不新增数据库表，不把日志写入数据库，不实现 `audit_logs` 持久化审计表。
- 不把首版日志基础设施下沉到 `packages/core`。
- 不记录 request / response body、完整 headers、SQL 参数、插件配置 secret、prompt 或交易密钥。
- 不按接口、actor、来源或状态码创建独立物理文件。
- 不新增业务 API route，不改变业务 API response envelope 的外部语义，除了补齐错误 `trace_id`。

## Decisions

### 1. API 私有 observability 模块

新增 `apps/api/src/quantagent/api/observability/`，首版职责保留在 API 层：

- `context.py`：使用 `contextvars` 管理 `request_id`、`trace_id`、`actor_type`、可选 `actor_id`、method、path、route 等上下文字段。
- `logging.py`：提供幂等 `configure_api_logging(settings)`，组装 logger、formatter、filter、queue 和 file handler。
- `formatters.py`：JSON Lines formatter，保证每条记录一行 JSON。
- `filters.py`：上下文字段注入和敏感字段脱敏。
- `files.py`：stream 到文件路径的映射、文件命名、小时/大小轮转和活跃文件判断。
- `queue.py`：队列化写入与队列满降级策略。
- `maintenance.py`：阶段 2 的关闭文件压缩、retention 清理、启动补偿清理和磁盘水位检查。
- `events.py`：稳定 event 名称常量。

不把这些能力放到 `packages/core`，因为当前真实复用方只有 `apps/api`。后续 worker/scheduler 需要复用时，应通过新的 issue/change 评估下沉边界。

日志 bootstrap 的生命周期与 FastAPI lifespan 对齐：`create_app()` 显式配置日志，lifespan shutdown 阶段应停止 queue listener、flush 已入队记录并关闭文件 handler。这个关闭路径必须幂等，测试多次创建和销毁 app 时不能留下后台线程、重复 handler 或未关闭文件描述符。

### 2. Request context 替代单一 request id middleware

现有 request id 能力演进为 request context middleware。中间件负责：

- 接受合法 `X-Request-ID`，不合法或缺失时生成新值。
- 优先从 W3C `traceparent` 解析 trace id，其次读取合法 `X-Trace-ID`，仍无则生成本地 trace id。
- 在请求进入时绑定 contextvars，在响应或异常完成后清理上下文。
- 过渡期内同时写入 contextvars 和 `request.state.request_id`，保证现有 `get_request_id(request)` 调用路径、响应 header、access log 和错误 envelope 一致。
- 回写 `X-Request-ID` 和 `X-Trace-ID` 响应 header。
- 输出一条 `http.request.completed` access log。

`get_request_id(request)` 保持请求标识的公共 accessor。实现时应让它优先读取 contextvars 中的 request id；没有 contextvars 时回退到 `request.state.request_id`；两者都缺失时按现有规则规范化请求头并写回 `request.state.request_id`。异常处理器读取同一上下文，把 `request_id` 和 `trace_id` 写入错误 envelope，避免 header、错误体和日志不一致。

### 3. Stream 分类和文件布局

日志默认写入：

```text
LOG_DIR/{stream}/YYYY/MM/DD/
```

默认 `LOG_DIR = RUNTIME_DIR/logs/api`。文档示例可以展示为 `runtime/logs/api/...`，但实现必须以 resolved `LOG_DIR` 为准，不能把仓库根目录 `runtime/` 字符串写死进文件管理逻辑。

stream 固定为：

- `access`：每个 HTTP 请求完成后的一条请求日志。
- `app`：应用启动、关闭、配置摘要、普通应用事件。
- `error`：未处理异常、5xx、DB readiness/session 失败等错误事件。
- `security`：登录失败、CSRF 失败、未授权、权限拒绝等安全事件。
- `audit`：受保护写操作、高风险动作或人工确认相关的审计事件日志。

`audit` stream 只表示文件审计事件日志，不等同于未来数据库 `audit_logs`。它不作为业务审计查询能力的验收。

文件名：

```text
{service}.{env}.{instance_id}.pid-{pid}.{stream}.{YYYYMMDDTHH}[.part-NNN].jsonl
```

示例：

```text
api.production.pod-api-7d9c9.pid-123.access.20260528T14.jsonl
api.production.pod-api-7d9c9.pid-123.access.20260528T14.part-002.jsonl
```

`instance_id` 由 `LOG_INSTANCE_ID` 配置提供；未配置时可使用主机名或本地兜底值。多进程通过 `pid` 隔离活跃文件，不使用跨进程锁写同一个文件。

占位符统一使用大写时间格式：目录为 `YYYY/MM/DD`，文件小时分片为 `YYYYMMDDTHH`。实现和测试都应按该格式解释，不再使用小写 `yyyy` 变体。

当前活跃文件的判定不依赖全局软链接。实现可以选择提供 `current/` 软链接或 marker 帮助人工排查，但它不是阶段 1 的验收要求；如果提供，必须保证软链接或 marker 不成为 writer 的状态真源。

### 4. 阶段 1 即队列化写入

阶段 1 必须引入队列化写入。请求路径只负责构造结构化日志记录并入队，不直接执行普通文件写入。后台 listener 从队列读取并写入对应 stream 文件。

队列满时的降级策略：

- `access` 使用非阻塞入队；队列满时可以丢弃、降采样或输出聚合丢弃计数。
- `app` 可按配置降级。
- `error`、`security`、`audit` 先尝试非阻塞入队；失败时允许走一个受限的 fallback writer 或 stderr 脱敏告警，避免关键事件被静默丢弃。
- fallback writer 只用于关键 stream 的降级路径，必须避免递归日志和无限阻塞；实现应设置最小限度的保护，例如单次告警、超时或进程内状态位。
- 队列满、降级和丢弃行为本身必须有内部计数或事件，便于测试和排查。
- 应用关闭时必须停止 listener 并 flush 已入队记录；如果超时仍未完成，应至少输出一次脱敏 stderr warning，并避免 shutdown 无限阻塞。

阶段 1 不做压缩、retention 和磁盘水位清理，但接口和任务边界必须为阶段 2 留出 maintenance 入口。

### 5. 轮转、压缩和 retention 分阶段

阶段 1 实现小时轮转和大小轮转：

- 当前小时变化时切换文件。
- 当前文件超过 `LOG_ROTATE_MAX_BYTES` 时追加 `part-NNN`。
- 活跃文件只负责写入和切换。

阶段 2 实现：

- 关闭文件压缩为 `.jsonl.gz`。
- 按 stream retention 清理过期文件。
- 启动时补偿处理上次退出后未压缩或已过期的关闭文件。
- 磁盘水位保护，至少支持 `LOG_MAX_TOTAL_BYTES`、`LOG_MIN_FREE_BYTES`、`LOG_ACCESS_DROP_WHEN_FULL` 或等价配置。

压缩和清理不得发生在请求路径，不得处理正在写入的活跃文件。

maintenance 判断“关闭文件”时必须排除当前进程正在写入的活跃文件，并通过文件名中的 `pid`、时间片、part 编号和 `LOG_MAINTENANCE_MIN_AGE_SECONDS` 或等价安全窗口，降低误处理其他仍存活进程文件的风险。对于无法确认是否关闭的文件，maintenance 必须跳过而不是强行压缩或删除。

### 6. 脱敏与字段边界

日志字段使用结构化 `extra` 或内部事件对象进入 formatter，不允许 route 函数拼接 JSON 字符串。

必须脱敏或禁止记录：

- `Authorization`
- `Cookie`
- `Set-Cookie`
- `X-CSRF-Token`
- `password`
- `token`
- `secret`
- `session`
- `DATABASE_URL` / 数据库连接串
- API key、broker credential、插件配置 secret、prompt 和交易密钥

普通日志只记录 `actor_type`；`security` 和 `audit` 事件可记录 `actor_id`。access 日志首版只记录 path，不记录 query string。后续如需要 query 排查，应单独设计白名单脱敏策略。

### 7. Uvicorn access log

API 自己输出结构化 `access` stream 后，应关闭或覆盖 `uvicorn.access`，避免同一请求出现两套格式不同的 access log。`uvicorn.error` 可以接入 `app` 或 `error` stream，但不得绕过脱敏和结构化格式。

## Risks / Trade-offs

- [Risk] 文件日志替代数据库审计真源。→ Mitigation：文档和 spec 明确 `audit` stream 不是业务审计查询能力，不实现 `audit_logs`。
- [Risk] 队列满导致高频 access 日志丢失。→ Mitigation：允许 access 丢弃或降采样，但 error/security/audit 尽量保留，并记录降级事件。
- [Risk] 阶段 2 改写阶段 1 已 review 契约。→ Mitigation：tasks 和验收要求阶段 2 不得重写 request context、formatter、stream 分类、文件命名和基础轮转契约。
- [Risk] 压缩或清理误碰活跃文件。→ Mitigation：文件管理模块必须区分活跃文件与关闭文件，测试覆盖“不压缩/不清理活跃文件”。
- [Risk] maintenance 误处理其他进程仍在写入的文件。→ Mitigation：通过 `pid` 文件名、安全时间窗口和保守跳过策略判断关闭文件；无法确认时不处理。
- [Risk] 日志初始化在 import 阶段产生副作用影响测试。→ Mitigation：`configure_api_logging(settings)` 必须幂等，并在 `create_app()` 内显式调用；测试可用临时目录和测试 settings。
- [Risk] 同步磁盘 IO 拖慢请求。→ Mitigation：阶段 1 即采用队列化写入，请求路径不做普通文件 IO。
