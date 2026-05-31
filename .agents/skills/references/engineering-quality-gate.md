# Engineering Quality Gate

本文件是 QuantAgent gh / OpenSpec / PR / Code Review skills 共用的工程质量门槛。它不是模板素材，而是执行前必须通过的检查清单。

工程规则必须前置到 issue、OpenSpec、implementation、PR 和 CR 全链路。CR 是最后一道检查，不是架构规范的唯一真源；任何会影响代码结构、目录边界、接口契约或验证方式的工作，都不能等到 review 阶段才第一次看到这些规则。

## 真源读取

开始 issue、OpenSpec、实现或 PR 前，必须先读与本轮范围直接相关的真源：

- 根目录 `AGENTS.md` 和被修改路径最近层级的 `AGENTS.md`。
- 关联 issue 正文、评论、PR 讨论和 review finding。
- 相关 `docs/design/`、`docs/prd/`、`openspec/changes/<change-id>/` 或 stable spec。
- 目标模块现有实现、测试和 README；涉及较新库时再查 lockfile、已安装版本和官方文档。

如果真源之间冲突，先说明冲突和取舍，不得直接按模型记忆或个人偏好实现。

## 模块 Gate 加载

按受影响路径加载共享模块 gate，不要把模块细则复制到每个 skill：

- 涉及 `apps/web/**` 时，必须读取 `.agents/skills/references/web-architecture-gate.md`。
- Web 变更涉及新增 feature、复杂 route、目录增长、shared 能力或文件职责拆分时，还必须读取 `.agents/skills/references/web-file-responsibility-and-feature-structure.md`。
- 涉及 `apps/api/**` 时，必须读取 `.agents/skills/references/api-architecture-gate.md`。
- 涉及 `packages/core/**`、`packages/plugin-sdk/**` 或 `plugins/**` 时，必须读取 `.agents/skills/references/core-and-plugin-architecture-gate.md`。

模块 gate 是规划和实现阶段的规范来源；`ai-code-review/references/**` 只补充审查场景、finding 口径和输出导航。

## 架构分层检查

新功能、跨文件改动或行为变化必须在进入实现前说清：

- 职责边界：哪些逻辑属于 route/page、service/provider、repository/port、schema/DTO、shared UI 或 package。
- 目录蓝图：计划新增或修改哪些目录、文件和模块，每个文件承担什么职责，是否需要新增 `AGENTS.md`、README、测试或生成入口。
- 复用点：哪些能力已经存在，哪些需要新增共享抽象，哪些不应提前抽象。
- 模型与接口：核心 model、DTO、schema、API、事件、配置、数据库字段或 TypeScript 类型的字段草案和所有权。
- 数据流：输入、状态真源、输出、错误路径和恢复方式。
- 失败路径：权限不足、外部依赖失败、配置缺失、并发或幂等风险。
- 验证入口：最小测试、契约检查、构建或人工验收方式。

禁止把页面、路由、服务、DTO、状态管理、API 调用和业务规则混写成一个大文件。只有存在多实现、稳定接口、外部适配、可替换策略、生命周期或持久化边界时，才引入 service、repository、port、adapter、strategy、registry、base class 等结构；不要为了设计模式本身制造抽象。

设计和实现前必须写清目录分层、文件职责、是否需要 README / usage note、哪些非显然边界需要中文注释，以及 runtime、API、query/hook、component、service、repository、DTO 或 schema 的边界。缺少这些内容时，先补 issue / OpenSpec / plan，不要直接编码。

## 前端质量门槛

涉及 `apps/web` 时必须检查：

- 已读取 `.agents/skills/references/web-architecture-gate.md`，并把其中的目标分层落实到 issue、OpenSpec、实现计划或 PR 说明。
- 复杂 feature、route、shared 能力或目录重组已读取 `.agents/skills/references/web-file-responsibility-and-feature-structure.md`，并写清目标文件职责。
- HeroUI v3 是基础组件库；按钮、输入、弹窗、表格、菜单、tabs、toast、tooltip 等优先 HeroUI。
- 样式默认使用 TailwindCSS 和现有 token；`*.module.css` 只用于 Tailwind 明显不适合的局部复杂样式。
- route 只负责页面入口、loader、search params 和组合；业务 API、query、mutation、hooks、组件、局部类型进入 `features/*`；跨模块基础能力进入 `shared/*`。
- 页面出现可复用区块、复杂状态、表单、表格、timeline、risk panel、权限状态、错误/空/加载态时，必须拆成命名组件和必要 hooks。
- 服务端状态必须通过 TanStack Query；页面不得裸 `fetch` 或手写后端 envelope / error 处理。
- `apiClient` 由 `app/runtime` 在运行时创建，不导出模块级全局单例；feature hooks 通过 runtime 的稳定 `apis` 对象访问业务 API。
- `BaseApi` 只做 path 与 transport helper；业务 endpoint 留在 feature API，不把 CRUD、分页、筛选或 query key 做进基类。
- 复杂 feature 和共享能力必须按 `api/`、`queries/`、`mutations/`、`hooks/`、`components/`、`types/`、`utils/`、`README.md` 等职责组织，不能长期平铺。
- 新 UI 必须覆盖 loading、empty、error、permission denied、sensitive masked 等状态，并保持管理台风格。

## 后端质量门槛

涉及 Python/API/core 时必须检查：

- 已读取对应模块 gate：涉及 `apps/api/**` 读取 `api-architecture-gate.md`；涉及 `packages/core/**` 或 `plugins/**` 读取 `core-and-plugin-architecture-gate.md`。
- FastAPI router 保持薄层，只处理 HTTP 参数、DTO、状态码、响应信封、依赖注入和异常映射；禁止 router 直接操作数据库、承载业务逻辑或调用插件。
- 业务流程、状态变化、插件生命周期、审计、权限、数据库写入或外部适配必须有明确 service/provider/repository/port 边界。
- DTO、ORM model、领域对象、插件 DTO、API envelope 分层独立，不能互相替代；ORM model 不能直接作为 API response 返回。
- 跨 app 复用能力优先下沉到 package；API 私有能力保留在 `apps/api`；core 不能反向依赖 app 或具体插件。
- Repository / storage port 只在存在真实持久化、跨调用复用或插件隔离需求时引入；service 依赖 repository 接口而非 ORM session 实现（依赖倒置）。
- 关键状态变化、高风险动作和人工确认必须可审计；审计记录 append-only，不可覆盖。

### 数据库操作

- 查询必须有 WHERE 条件和索引覆盖；禁止无 LIMIT 大查询和 `SELECT *`；`.all()` 不加 `limit` 是 must-fix。
- ORM 关联加载必须显式声明 `selectinload` / `joinedload`；循环内访问 relation attribute（N+1）是 must-fix。
- 写事务范围最小化，事务内禁止跨网络调用（HTTP、插件 invoke）；批量写入必须分批。
- Engine 由应用生命周期管理，禁止模块级 `create_engine()` 单例；pool size 可配置。
- 软删除必须处理 unique 约束（条件索引）、默认过滤和唯一性冲突错误。
- Migration 禁止手改历史、大表同步删列/改类型；data backfill 必须分批。

### 缓存策略

- 没有性能瓶颈证据前不引入缓存；先看查询优化和索引。
- 引入缓存前必须说明：缓存什么、失效策略、一致性保证级别、内存上限。
- 缓存不能改变业务语义——有缓存和无缓存的行为必须一致。

### 并发与异步

- async endpoint 内禁止同步阻塞调用（`requests`、同步 DB driver、CPU 密集）；必须用 `run_in_executor` 或换 async 库。
- 共享状态的先读后写必须有并发保护（乐观锁 version field 或悲观锁 `SELECT ... FOR UPDATE`）。
- API 写操作必须幂等或通过 idempotency key 保证；插件调用和事件发布必须可安全重试。
- 所有外部调用必须有显式超时；插件执行必须有可配置超时上限和降级策略。
- 并发相关代码必须有测试覆盖（竞态、幂等、超时降级）。

### 跨功能调用

- 调用链必须是 router → service → repository；跳层（router 直接调 repository 或 ORM）是 must-fix。
- 跨聚合不直接调对方 repository；通过 service 接口或事件通信。
- 插件之间不能互相 import；只能通过 core 定义的 event / DTO 通信。

### 错误处理与可观测性

- 不吞异常（`except Exception: pass` 是 must-fix）；底层错误必须 wrap 成领域异常。
- 错误响应使用统一 envelope，不暴露 traceback、连接串、secret 或内部路径。
- 每个 HTTP 请求必须有 `X-Request-ID`，贯穿日志、错误响应和审计。
- 关键路径必须有结构化日志（JSON + request_id + action + duration）；日志不打印 secret。
- 插件执行必须有 duration + success/failure 指标。

### 插件边界

- 插件只通过 `plugin.yaml` + Registry 进入系统；core 不硬编码插件 class/import/if-else。
- 插件执行必须有超时保护、返回值大小限制和失败隔离。
- 插件之间互相隔离，不能互相 import 或直接访问数据库 session。
- 插件配置中的 secret 只存 reference，不存明文。

## 注释门槛

代码不需要解释显而易见的语句，但这些地方必须写短注释说明意图或取舍：

- 安全边界、权限、审计、状态机、并发、幂等、重试、降级和敏感信息脱敏。
- 协议适配、第三方 API 差异、框架限制、生成物边界和非显然兼容策略。
- 为避免提前抽象而刻意保留简单实现，或为复用/扩展而引入抽象的理由。

注释应说明“为什么这样做”，不要复述代码在做什么。

## OpenSpec 质量门槛

OpenSpec artifacts 必须能指导实现，不能只是空泛愿景：

- `proposal.md` 说明 why now、当前缺口、非目标和风险边界。
- `design.md` 是实现蓝图，必须说明目录/文件规划、分层架构、模块职责、核心模型、DTO/schema/API/事件/配置/数据库字段草案、数据流、失败路径、复用/不复用的取舍和验证策略。
- `specs/**/spec.md` 用 requirement 和 scenario 描述可验证行为，不写实现流水账。
- `tasks.md` 体现依赖关系、可并行边界、写入范围、review gate 和验证动作。

如果 artifacts 没有说明目录/文件规划、职责边界、核心模型与接口字段、复用点、失败路径或验证方式，不能进入实现；先补强 artifacts 或向维护者追问。

## PR 证据链门槛

PR 说明必须写清：

- 关联 issue / OpenSpec change / 设计文档依据。
- 为什么这样拆分，为什么新增或不新增抽象。
- 改动摘要按边界组织，不按文件流水账。
- 实际运行的验证命令和结果。
- 未验证项、残余风险、非目标，以及跳过组件拆分、注释或抽象的理由。
