# API Architecture Gate

本文件是 `apps/api` 在 issue、OpenSpec、implementation、PR 和 Code Review 阶段共用的目标架构门槛。它比 CR 场景细则更靠前：规划和写代码前必须先用它约束目录、职责、数据流和运行时行为。

现有代码只能作为迁移背景，不能自动成为新代码模板。新增或修改代码应向本文件定义的目标边界收敛；未触碰的历史债务可以记录为 residual risk 或后续 issue。

## 默认分层

`apps/api/src` 默认按职责分层：

- `routers/`：HTTP 入口，只处理请求解析、DTO 校验、依赖注入、状态码映射和响应信封。不放业务逻辑、数据库写入、插件操作或状态流转。
- `schemas/`：request/response DTO 定义，字段校验和序列化规则。不放业务逻辑、数据库查询或服务调用。
- `services/`：业务流程编排，承载状态变化、插件生命周期、权限检查、审计记录和跨聚合协调。不处理 HTTP 协议细节。
- `repositories/`（或 `ports/`）：持久化边界，只做 ORM 映射和数据库查询。不承载业务规则，不被 router 直接调用。
- `models/`（ORM）：数据库表映射，只做字段定义和关系声明。不混入 API DTO、业务逻辑或序列化逻辑。
- `middleware/`：横切关注点，只处理认证、日志、CORS、request ID、错误转换等全局逻辑。不放业务域规则。
- `config/`：应用配置，环境变量加载和校验。默认值必须支持最小启动，缺失敏感配置时错误信息不泄密。

复杂 feature 建议目录：

```text
apps/api/src/quantagent/api/
  routers/v1/         # HTTP 路由，按资源组织
  schemas/            # request / response DTO
  services/           # 业务编排
  repositories/       # 持久化边界（需要时）
  middleware/          # 横切关注点
  config/             # 配置
```

当 API 变更涉及新增 router、新增 service、目录增长或跨层调用时，必须继续读取 `.agents/skills/ai-code-review/references/api/overview.md` 的场景索引。

## 文件职责矩阵

| 文件 / 目录 | 只负责 | 禁止放入 |
| --- | --- | --- |
| `routers/**` | HTTP 参数解析、DTO 校验调用、DI 注入、状态码、`ApiResponse[T]` 包装、调用 service | 业务逻辑、`session.execute()`、`session.add()`、插件操作、状态流转、if-else 业务分支 |
| `schemas/**` | request/response 字段定义、Pydantic 校验、DTO 映射边界 | 业务逻辑、数据库查询、service 调用、ORM model 直接暴露 |
| `services/**` | 业务流程编排、状态变更、权限检查、审计、跨聚合协调、插件生命周期 | HTTP 状态码、request/response 解析、直接 SQL、ORM 关系声明 |
| `repositories/**` | ORM 映射、数据库查询构造、批量操作、分页查询 | 业务规则、HTTP 协议、API DTO、直接被 router 调用 |
| `models/**` | ORM 表映射、字段定义、关系声明、索引声明 | API DTO、序列化逻辑、业务方法、直接作为 response 返回 |
| `middleware/**` | 认证、日志、CORS、request ID、错误转换、速率限制 | 业务域逻辑、特定资源的 CRUD、插件操作 |

## 拆分触发阈值

同一文件中如果同时出现以下 3 类以上，必须拆分到职责文件；如果出现在 router 中，通常是 `must-fix`：

- 数据库操作：`session.execute()`、`session.query()`、`session.add()`、`db.execute()`、ORM relation 访问。
- HTTP 协议：status code、`JSONResponse`、`ApiResponse`、request body 解析、query param。
- 业务逻辑：状态判断、if-else 分支、权限检查、审计记录、跨资源协调。
- DTO / schema：request field 校验、response field 映射、OpenAPI schema。
- 插件操作：registry 调用、plugin invoke、生命周期管理。
- 外部调用：HTTP client、消息队列、缓存操作。

拆分不是按行数触发；一个 40 行 router 同时执行 DB 查询、状态判断和插件调用，比一个 150 行纯查询构造更需要拆。

## Router 与 Service 边界

Router 保持 HTTP 薄层，核心职责：

1. 接收请求，用 schema 校验参数。
2. 通过 DI 获取 service 实例。
3. 调用 service 方法，传入 DTO。
4. 将 service 返回的领域对象或 DTO 包装为 `ApiResponse[T]`。
5. 映射领域异常到 HTTP 状态码。

Router 不做的事情：

- 不直接操作数据库 session。
- 不包含业务判断逻辑（权限、状态流转、规则校验）。
- 不直接调用插件 registry 或 runtime。
- 不直接处理缓存。
- 不在 router 内部做跨资源编排。

Service 是业务真源，核心职责：

1. 接收 DTO，执行业务规则校验。
2. 通过 repository/port 操作持久化。
3. 编排跨聚合操作。
4. 触发审计和事件。
5. 管理插件生命周期。
6. 返回领域对象或 DTO 给 router。

## DTO / Envelope / Contract

### 分层独立性

以下类型必须严格分离，不能互相替代：

- **request DTO**（`schemas/`）：API 入参校验和文档，字段由 API 契约决定。
- **response DTO**（`schemas/`）：API 出参结构和文档，字段由 API 契约决定。
- **领域对象**（service 层内部）：业务操作的结构化输入输出，不受 HTTP 契约约束。
- **ORM model**（`models/`）：数据库表映射，字段由持久化需求决定。
- **插件 DTO**（`plugin-sdk`）：插件输入输出边界，由插件类型契约决定。

### 映射规则

- Router 负责 request DTO → service 层输入 的适配。
- Router 负责 service 层输出 → response DTO 的适配。
- Service 负责领域对象 ↔ repository 输入输出的适配。
- 映射逻辑集中，不散落在各处。

### Envelope

所有 API 响应必须使用统一信封：

```python
ApiResponse[T]:
    code: int       # 业务码，0 表示成功
    data: T | None  # 业务数据
    msg: str        # 人类可读消息
    error: ...      # 错误详情，仅失败时
```

- Router 必须通过 `ApiResponse[T]` 返回，禁止返回裸 dict、ORM model 或领域对象。
- OpenAPI schema 必须反映真实 envelope 结构。
- Error response 同样使用 envelope，不返回裸 traceback 或 HTTP 原生错误。

### 契约稳定性

- API v1 路由注册必须通过 `register_api_v1_routes` 统一管理。
- Response field 命名一旦公开就不可随意更改；需要变更时先加新字段，旧字段标记 deprecated。
- Error code 必须可枚举，新增 error code 必须在文档中登记。
- 跨端字段变化（前端 ↔ API）需要同步检查 contracts / schema / OpenSpec。

## DB 操作规范

### 查询安全

- **禁止扫全表**：所有查询必须有 WHERE 条件；分页查询必须走索引覆盖；ORM 的 `.all()` 不加 `limit` 就是 `must-fix`。
- **N+1 查询**：ORM 关联加载必须用 `selectinload` / `joinedload` 显式声明；禁止在循环内触发 lazy load。在循环内访问 relation attribute（如 `for item in items: item.author.name`）是 `must-fix`。
- **禁止 SELECT ***：明确列出需要的字段；大表查询必须用 `only()` / `load_only()` 限制返回列。
- **分页必须有上限**：`limit` 不超过可配置的最大值（如 100）；不传 `limit` 时使用安全默认值。

### 事务边界

- 写事务范围最小化：只在需要原子性的操作组外加事务。
- 长事务禁止跨网络调用：事务内不允许 `await httpx` / `await plugin.invoke` / `await cache.get`。
- 读操作默认不包事务，或使用 read-only session。
- 批量写入必须分批，单批大小可配置。
- 事务失败必须 rollback；session 使用 context manager 或 try/finally 确保归还。

### 连接池

- Engine 创建由应用生命周期管理（lifespan），禁止模块级 `engine = create_engine()` 单例。
- Pool size 和 max overflow 必须可配置。
- Health check 不依赖 DB 连接；Ready check 只验证 DB 可达。

### 软删除

如果使用软删除（`deleted_at` / `is_deleted`）：

- Unique 约束必须加条件索引（`WHERE deleted_at IS NULL`）。
- 所有查询默认过滤 `deleted_at IS NULL`；ORM 可用 query filter 或 mixin 自动处理。
- 唯一性冲突必须有明确错误信息，不暴露为数据库约束违反。
- 硬删除策略必须明确（如定期清理任务，默认 30 天后硬删）。

### Migration 安全

- 禁止删列、改类型的大表同步 migration；data backfill 必须分批。
- Column rename 必须分步：先加新列 → 迁移数据 → 再删旧列。
- 禁止手改或重排 Alembic migration 历史。
- 新增 migration 必须在本地验证 `alembic upgrade head` 和 `alembic downgrade -1`。

## 缓存策略

### 引入原则

- 缓存不是银弹：没有证据证明是性能瓶颈前不引入缓存；先看查询优化和索引。
- 引入缓存前必须说明：缓存什么、失效策略、一致性保证级别、内存上限。
- 缓存层不能改变业务语义——有缓存和无缓存的行为必须一致。

### 失效策略

- 写入时主动失效优先于 TTL 过期。
- 失效粒度必须跟查询粒度匹配：按资源 ID 失效，不按模糊 pattern 批量清。
- 批量操作后必须批量失效相关缓存 key。

### 防护

- **缓存穿透**：空值缓存 + 短 TTL；查询不存在的 key 不穿透到 DB。
- **缓存击穿**：hot key 预热或互斥锁重建。
- **缓存雪崩**：TTL 加随机偏移，避免大面积同时过期。
- **缓存 key 设计**：必须有 namespace + 业务维度 + 版本标识；禁止用用户输入直接拼 key。

### 一致性

- 写后读场景必须说明一致性保证级别（强一致 / 最终一致）。
- 插件配置、Registry 数据这类低频变更可以接受最终一致。
- 缓存数据不得作为审计或决策的唯一真源。

## 并发与异步

### async/await 边界

- FastAPI async endpoint 内禁止同步阻塞调用：`requests.get()`、同步 DB driver、CPU 密集计算。
- 同步阻塞必须用 `run_in_executor` 或替换为 async 库。
- 同步路由函数（`def` 而非 `async def`）由 FastAPI 线程池执行，适用于 CPU 密集或同步库调用。

### 竞态条件

- 共享状态修改必须有并发保护：乐观锁（version field）或悲观锁（`SELECT ... FOR UPDATE`）。
- 先读后写（read-modify-write）模式必须有锁保护，否则是 `must-fix`。
- 分布式场景考虑分布式锁或数据库 advisory lock。

### 幂等性

- API 写操作必须天然幂等或通过 idempotency key 保证。
- 插件调用、事件发布必须可安全重试，重试不产生副作用。
- 幂等实现必须注释说明策略。

### 超时控制

- 所有外部调用（DB、HTTP、插件执行）必须有显式超时。
- 插件执行必须有可配置的超时上限和降级策略。
- DB statement timeout 必须可配置。
- HTTP client timeout 不使用默认无限等待。

### 资源限制

- 批量操作必须有 batch size 上限。
- 并发任务数必须可配置。
- 大结果集必须分页或流式返回，不一次性加载到内存。

### 并发测试要求

并发相关代码必须有测试覆盖：

- 竞态条件：用 `asyncio.gather` 模拟并发写入，验证数据一致性。
- 幂等性：相同请求重复调用，验证结果不变且无副作用累积。
- 超时：mock sleep 或慢响应，验证超时降级路径。
- 资源限制：超出 batch size 或并发上限时验证拒绝或排队行为。

## 跨功能调用

### 调用方向规则

- Router → Service：允许，通过 DI 注入。
- Service → Repository：允许，通过 DI 注入。
- Service → Service：允许，但仅限同聚合或通过明确接口。跨聚合优先走事件。
- Router → Repository：**禁止**，是 `must-fix`。
- Router → ORM Model：**禁止**，是 `must-fix`。
- Feature A Service → Feature B Repository：**禁止**，是 `must-fix`。跨聚合通过 service 接口或事件通信。

### 跨聚合通信

- 同步调用：通过 service 方法，走 DI 注入。
- 异步解耦：通过事件总线，发布领域事件。
- 不 import 对方的 repository 或 ORM model。

### 插件隔离

- 插件之间不能互相 import，只能通过 core 定义的 event / DTO 通信。
- Service 不直接 import 具体插件实现，通过 Registry + plugin-sdk 抽象访问。

## 错误处理链

### 基本规则

- 不吞异常：禁止 `except Exception: pass` 或空 `except` 块。
- 不裸 `except Exception`：捕获范围尽可能精确，至少区分业务异常和系统异常。
- 底层错误必须 wrap 成领域异常向上传播：`raise ServiceError(...) from original_error`。
- 不在 service/repository 层返回 HTTP status code；HTTP 映射只在 router 层。

### 错误响应

- 所有错误响应必须使用统一 envelope，包含 `code` / `msg` / `error`。
- 禁止在错误响应中暴露 traceback、数据库连接串、secret、token 或内部路径。
- 生产环境禁止返回 debug 级别的错误详情。
- 错误信息必须包含 request ID 以便追踪。

### 异常层次

- `DomainError`：业务规则违反（如状态不可变更、资源不存在）。
- `ConcurrencyError`：乐观锁冲突、竞态条件。
- `ExternalError`：外部依赖（DB、Redis、插件宿主）不可用。
- `ValidationError`：输入校验失败（schema 层已处理，service 层补充业务校验）。

## 可观测性

### 日志

- 结构化日志：JSON 格式，包含 `request_id`、`action`、`duration_ms`、`status`。
- 关键路径必须有日志：请求进入、业务操作开始/完成、插件调用、外部依赖调用、错误发生。
- 日志禁止打印 secret、token、password、API key、数据库连接串。
- 日志级别使用正确：`INFO` 记录正常业务操作，`WARNING` 记录可恢复异常，`ERROR` 记录需要关注的失败。

### Request ID

- 每个 HTTP 请求必须有唯一 `X-Request-ID`。
- Request ID 必须贯穿整个调用链：日志、错误响应、审计记录。
- 如果上游传入 `X-Request-ID`，优先使用；否则自动生成。

### 审计

- 关键状态变更（插件启停、配置变更、决策生成、审批操作）必须可审计。
- 审计记录必须包含：actor、action、resource、timestamp、request_id、变更前后状态。
- 审计记录 append-only，不可覆盖或删除。

### 指标

- 插件执行必须有 `duration_ms` + `success/failure` 指标。
- DB 查询耗时超过阈值必须有慢查询日志。
- 外部调用失败率必须有监控。

## 注释规范

代码不需要解释显而易见的语句，但这些地方必须写短注释说明意图或取舍：

- **安全边界**：`# 权限检查：仅 admin 角色可触发插件重载`
- **状态机 / 流转**：`# 状态流转：pending → approved → executing → done/failed，不允许回退`
- **并发 / 锁**：`# 乐观锁：version 字段防止并发覆盖，冲突时抛 ConcurrencyError`
- **非显然取舍**：`# 选择同步执行而非入队：因为需要实时返回结果，牺牲了吞吐量`
- **协议适配**：`# 第三方 API v10 要求 X-Signature 校验，不可跳过`
- **软删除逻辑**：`# 软删除：查询默认过滤 deleted_at IS NULL，清理任务 30 天后硬删`
- **缓存失效**：`# 写入后主动删缓存，不依赖 TTL，保证下次读拿到最新`
- **刻意简单**：`# 未引入 Repository 抽象：当前只有单 DB 实现，无复用需求`
- **幂等性**：`# 幂等：相同 request_id 重复调用返回上次结果，不重复执行`
- **超时策略**：`# 插件执行超时 30s，超时后标记 failed 并通知，不无限等待`
- **批量操作**：`# 分批写入，每批 500 条，避免单事务过大导致锁升级`

注释应说明"为什么这样做"，不要复述代码在做什么。

## 规划和 Review 口径

- Issue / OpenSpec 规划阶段必须写清目录蓝图、文件职责、service/router/repository/model/DTO 边界、数据流、失败路径和验证入口。
- PR 阶段必须说明实现是否遵循本 gate；偏离时说明原因、风险和后续收敛点。
- Code Review 阶段只对当前 diff 中新增或扩大债务的问题给 actionable finding；未触碰历史问题列 residual risk / defer。

`must-fix` 信号：

- Router 直接执行数据库操作（`session.execute()`、`session.add()`）。
- Router 直接返回 ORM model、裸 dict 或绕过 `ApiResponse[T]`。
- Router 内包含业务判断逻辑（权限、状态流转、规则校验）。
- 查询无 WHERE / 无 LIMIT / 无索引覆盖，存在扫全表风险。
- N+1 查询：循环内访问 ORM relation attribute。
- async endpoint 内调用同步阻塞操作（`requests.get()`、同步 DB driver）。
- 先读后写无锁保护，存在竞态条件。
- 跨聚合直接调 repository 或 ORM model。
- `except Exception: pass` 或空 `except` 块。
- 错误响应暴露 traceback、secret、连接串或内部路径。
- 新增 route 未通过 `register_api_v1_routes` 统一注册。

`should-fix` 信号：

- 当前 PR 内低成本可以把 DB 操作移到 repository / service。
- service 层返回 HTTP status code 或依赖 HTTP 协议细节。
- DTO 映射散落在多处而非集中适配。
- 查询未用 `load_only()` / `only()` 限制返回列，但暂无性能问题。

`defer` / `residual risk` 信号：

- 历史代码已有但当前 PR 未触碰的不规范结构。
- 需要专门迁移 issue 才能解决的大范围分层问题。
- 缓存策略缺失但当前无性能瓶颈证据。

## 验收测试指导

### 测试层次与覆盖要求

后端变更必须有匹配的测试覆盖，不能只靠"本地跑通"或"手动验证"。按变更风险选择最小有效测试层次：

| 变更类型 | 必须覆盖 | 建议覆盖 |
| --- | --- | --- |
| 新增 / 修改 router | 运行时响应 + `/openapi.json` 契约 | 错误路径、认证失败、参数边界 |
| 新增 / 修改 service | 业务规则正确路径 + 至少一条失败路径 | 并发、幂等、外部依赖 mock |
| 新增 / 修改 repository | CRUD 基本路径 + 查询条件覆盖 | 批量操作、分页边界、软删除过滤 |
| 新增 / 修改 DTO / schema | 序列化 / 反序列化 + 校验规则 | 边界值、缺失字段、类型不匹配 |
| 新增 / 修改 middleware | request ID 传递 + 错误转换 | 认证失败、CORS、敏感信息脱敏 |
| 数据库 migration | `upgrade` + `downgrade` 可执行 | 数据 backfill 正确性 |
| 并发 / 异步相关 | 竞态条件 + 幂等性 | 超时降级、资源限制 |

### 测试编写原则

- **测试行为，不测实现**：验证 service 返回正确结果和副作用，不验证内部用了哪个 ORM 方法。
- **每条测试只验证一个行为**：一个 test 方法只 assert 一个关注点；混合正常路径和错误路径的测试难以定位失败原因。
- **mock 边界要准**：只 mock 外部边界（DB、HTTP client、插件调用），不 mock 同层依赖。mock 过多说明被测代码职责不清或需要重构。
- **测试数据要隔离**：每个 test 方法使用独立数据，不依赖其他测试的执行顺序或残留状态。
- **失败路径必须测**：每个业务规则至少有一条测试验证违反规则时的行为（错误类型、错误信息、状态不变）。

### 测试命名与组织

- 测试文件与被测文件对应：`routers/v1/plugins.py` → `tests/test_plugins_router.py`。
- 测试方法命名描述行为：`test_list_plugins_returns_envelope`、`test_create_plugin_without_auth_returns_401`。
- 测试目录结构反映源码结构，不把所有测试堆在一个文件里。

### 验证命令

按 `apps/api/README.md` 中的本地验证命令执行最小验证：

```bash
cd apps/api && uv run python -m unittest discover -s src
```

改动 Docker、迁移或数据库连接路径时，从仓库根目录验证对应 compose/migration 流程。

完成后说明改了哪些文件，以及实际跑过哪些验证；如果因为环境缺失无法验证，要明确说明缺口。

## 文档回写规则

对系统架构、平台能力、API 契约或工程规范有影响的变更，必须及时回写对应文档。不能只留在代码或 PR 说明里。

### 回写判断

变更完成后必须判断是否需要回写，按以下实例评估：

| 变更场景 | 回写目标 | 优先级 |
| --- | --- | --- |
| 新增 API endpoint、修改 response 结构或 error code | `apps/api/AGENTS.md` 路由骨架、`docs/design/08-api-and-websocket-design.md` | 高 |
| 新增 service / repository 层或修改分层约定 | `apps/api/AGENTS.md` API 边界、本 gate 文件 | 高 |
| 修改数据库表结构、新增 ORM model 或迁移策略 | `packages/core/AGENTS.md`、`docs/design/04-database-and-persistence-design.md` | 高 |
| 新增插件类型、修改 Registry 接口或插件生命周期 | `plugins/AGENTS.md`、`packages/plugin-sdk/AGENTS.md`、`docs/design/03-plugin-system-and-registry.md` | 高 |
| 新增 package 或修改 package 依赖方向 | 根 `AGENTS.md` 项目边界、`docs/design/01-tech-stack-and-project-structure.md` | 高 |
| 修改工程规范（本 gate 文件、engineering-quality-gate.md） | 根 `AGENTS.md` 工程质量硬门槛 | 中 |
| 修改配置加载、环境变量或启动流程 | `apps/api/AGENTS.md` 配置节、`apps/api/README.md` | 中 |
| 新增或修改横切能力（middleware、错误处理、日志） | 本 gate 文件、`apps/api/AGENTS.md` | 中 |
| 局部 bug 修复或纯实现细节调整 | 通常不需要回写 | 低 |

### 回写原则

- **按具体实例判断**：不是所有变更都需要回写；只回写对后续开发和协作有长期影响的规则和约定。
- **回写最小有效范围**：不重写整篇文档，只补充或修正受影响的部分。
- **PR 中说明回写**：如果回写了文档，在 PR 说明中列出更新了哪些文档以及原因；如果判断不需要回写，也要说明理由。
- **不要过度回写**：一次性实现细节、临时 workaround、未确认的想法不回写到长期文档。
- **gate 文件和 AGENTS.md 互补**：gate 定义目标架构和审查口径，AGENTS.md 记录当前约定和行为约束。两者不要重复。
