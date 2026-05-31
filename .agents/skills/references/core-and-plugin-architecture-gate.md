# Core & Plugin Architecture Gate

本文件是 `packages/core`、`packages/plugin-sdk` 和 `plugins/**` 在 issue、OpenSpec、implementation、PR 和 Code Review 阶段共用的目标架构门槛。它比 CR 场景细则更靠前：规划和写代码前必须先用它约束 package 边界、插件分层、数据流和运行时行为。

现有代码只能作为迁移背景，不能自动成为新代码模板。新增或修改代码应向本文件定义的目标边界收敛；未触碰的历史债务可以记录为 residual risk 或后续 issue。

## Package 边界与依赖方向

### 依赖方向（不可逆）

```text
apps/api → packages/core → packages/plugin-sdk ← plugins/*
```

- `packages/core` 不能反向依赖 `apps/api`、FastAPI、React 或任何具体 app。
- `packages/core` 不能依赖具体插件实现（`plugins/*`）。
- `packages/plugin-sdk` 是插件唯一依赖；插件不能直接 import core 内部实现。
- `apps/api` 私有能力保留在 `apps/api`；跨 app 复用能力下沉到 `packages/core`。

### 违反信号

以下情况是 `must-fix`：

- `packages/core` 的 import 中出现 `fastapi`、`starlette`、`apps.api`、`plugins.*`。
- API envelope（`ApiResponse`、HTTP status code）进入 core。
- 前端展示逻辑（React、TypeScript 类型）进入 core。
- 插件直接 import core 的内部模块（registry 实现细节、ORM model 等）。

### 新增共享能力的门槛

只有满足以下条件才在 `packages/core` 新增能力：

- 至少有 2 个调用方（当前或近期计划）。
- 职责稳定，不会随业务需求频繁变更。
- 不引入对 apps 或具体插件的依赖。
- 不为了设计模式本身制造抽象。

## 默认分层

### packages/core

```text
packages/core/src/quantagent/core/
  config/         # 应用配置、环境变量、默认值、校验
  db/             # engine、session 工厂、migration 配置
  registry/       # 插件发现、manifest 校验、Registry 服务
  runtime/        # 插件加载、生命周期、执行隔离
  model_config/   # 模型配置管理
  event/          # 事件模型、事件总线（未来）
```

### packages/plugin-sdk

```text
packages/plugin-sdk/src/quantagent/plugin_sdk/
  base.py         # BasePlugin、RuntimePlugin Protocol
  context.py      # RuntimeContext，插件执行上下文
  dto.py          # 插件输入输出 DTO：SourceFetchInput/Result、NotificationSendInput/Result 等
  errors.py       # 插件级错误定义
```

### plugins

```text
plugins/
  sources/              # 数据源插件
    <plugin-name>/
      plugin.yaml       # manifest
      src/              # 插件实现
      config.schema.json  # 配置 schema
      tests/            # 插件测试
  notifications/        # 通知插件
  brokers/              # 交易执行插件
```

## 插件分层与 DTO 边界

### 四层架构

```text
plugin.yaml（manifest）  →  PluginRegistry（发现/验证）  →  RuntimeService（加载/执行）  →  Plugin DTO（输入输出边界）
```

每层职责和边界：

| 层 | 只负责 | 禁止放入 |
| --- | --- | --- |
| `plugin.yaml` | 插件元数据声明：id、name、type、version、entrypoint、capabilities、config_schema、permissions | 逻辑、代码、依赖注入 |
| `PluginRegistry` | 发现插件目录、校验 manifest 完整性、维护插件记录状态、提供查询接口 | 执行插件代码、直接 import 插件实现、硬编码插件列表 |
| `RuntimeService` | 加载插件 entrypoint、管理生命周期（load/start/stop/health_check）、执行隔离、超时控制 | 了解插件业务逻辑、修改插件状态 |
| `Plugin DTO` | 定义输入输出边界：类型校验、字段约束、序列化 | 业务逻辑、HTTP 协议、ORM 映射 |

### 插件 DTO 与其他类型的关系

以下类型必须严格分离：

- **插件 DTO**（`plugin-sdk/dto.py`）：插件输入输出契约，由插件类型决定。
- **API request/response DTO**（`apps/api/schemas/`）：HTTP 契约，由 API 版本决定。
- **ORM model**（`packages/core/db/`）：数据库表映射，由持久化需求决定。
- **领域对象**（service 层内部）：业务操作的结构化输入输出。

映射规则：

- API 层负责 API DTO ↔ 插件 DTO 的适配。
- Service 层负责领域对象 ↔ 插件 DTO 的适配。
- 插件只看到 plugin-sdk 定义的 DTO，不接触 API DTO 或 ORM model。

### 插件类型与 DTO 契约

每种插件类型有固定的 DTO 契约：

| 插件类型 | 输入 DTO | 输出 DTO | 能力声明 |
| --- | --- | --- | --- |
| source | `SourceFetchInput` | `SourceFetchResult` | `source.fetch` |
| notification | `NotificationSendInput` | `NotificationSendResult` | `notification.send` |
| broker | `BrokerExecuteInput` | `BrokerExecuteResult` | `broker.execute` |
| industry | 预留 | 预留 | 预留 |
| strategy | 预留 | 预留 | 预留 |

新增插件类型时，必须在 `plugin-sdk/dto.py` 中定义对应 DTO，并通过 design doc 同步更新。

## Registry 与插件边界

### 注册与发现

- 所有插件必须通过 `plugin.yaml` 注册；禁止硬编码插件列表或 if-else 分发。
- Registry 只负责发现和校验，不执行插件代码。
- 插件 ID 格式：`quantagent.official.<type>.<name>` 或 `quantagent.community.<type>.<name>`。

### 加载路径安全

- 插件 entrypoint 格式必须是 `{module}:{attribute}`。
- 加载时必须校验路径安全：禁止目录穿越（`..`），禁止访问插件目录外的文件。
- 错误信息必须脱敏：不暴露服务器路径、绝对路径或敏感配置。

### 插件状态生命周期

```text
discovered → validated → installed → configured → loaded → started → stopped → disabled → uninstalled
```

- 状态流转必须 append-only 可回放。
- 状态变更必须可审计：记录 actor、action、timestamp、变更前后状态。
- 插件加载失败不阻塞其他插件；失败状态必须记录并通知。

### 插件隔离

- 插件之间不能互相 import；只能通过 core 定义的 event / DTO 通信。
- 插件不直接访问数据库 session；需要持久化时通过 core 提供的接口。
- 插件不直接访问系统配置；只接收 `RuntimeContext` 提供的配置。

## 插件性能边界

插件 `invoke()` 是性能热点，必须定义明确边界：

### 执行隔离

- 同步插件必须通过 `run_in_executor` 执行，不阻塞事件循环。
- 每个插件执行必须有可配置的超时上限（默认 30s），超时后标记 failed 并通知。
- 插件执行失败不级联影响其他插件或核心服务。

### 资源限制

- 插件返回值必须有大小限制（如 1MB），防止内存溢出。
- 插件执行期间禁止无限循环；超时机制作为兜底。
- 批量操作必须有 batch size 上限。

### 缓存与预热

- Registry 扫描结果可以缓存，但插件状态查询必须实时或短 TTL。
- 插件配置变更后必须失效相关缓存。
- 热门插件的元数据可以预热，但不预热插件实例。

## 事件 / 状态 / 审计

### 事件驱动

- 状态变更（插件启停、决策生成、审批完成）通过事件解耦。
- 事件发布者和消费者不直接依赖对方的具体实现。
- 事件 payload 必须有版本标识，支持向后兼容演进。

### 状态管理

- 状态流转 append-only，不可覆盖历史状态。
- 主表与审计记录必须在同一事务内写入。
- 状态变更必须保存完整上下文：谁（actor）在什么时候（timestamp）做了什么（action），变更前后的值。

### 审计

- 审计记录 append-only，不可删除或覆盖。
- 审计必须覆盖：插件生命周期、配置变更、决策生成、审批操作、外部依赖调用结果。
- 审计 payload 不存储 secret 明文，只存 reference（如 `secret_ref: "vault://xxx"`）。

### 敏感数据

- 插件配置中的 secret 只存 reference，不存明文。
- 日志、错误响应和测试快照必须脱敏。
- 审计 payload 中的敏感字段（API key、token、prompt、私有策略）必须标记或遮盖。

## ORM 与 Repository 规范

### ORM Model 职责

- 只做数据库表字段映射和关系声明。
- 可以包含索引声明和约束声明。
- 不混入业务方法、序列化逻辑、API DTO 映射或状态机逻辑。

### Repository / Port

- 只在存在真实持久化、跨调用复用或插件隔离需求时引入。
- Repository 接口按聚合根拆分，不要一个大接口满足所有场景。
- Repository 不承载业务规则，不做状态判断。
- 不被 router 直接调用；调用链必须是 router → service → repository。

### 依赖倒置

- Service 依赖 repository 接口（Protocol 或 ABC），而非 ORM session 实现。
- Repository 实现通过 DI 注入到 service。
- 高层模块（service）不依赖低层实现细节（具体 ORM 查询构造）。

### 查询规范

- 复杂查询封装在 repository 方法内，不散落在 service 各处。
- 查询必须走索引；N+1 查询必须用 `selectinload` / `joinedload` 解决。
- 大表查询必须限制返回列和行数。
- 批量操作必须分批执行。

## 配置与 Secret 管理

### 配置分层

- `core/config/` 只放跨 app 共享的配置和默认值。
- API 私有配置（如 CORS origin、rate limit）保留在 `apps/api/config/`。
- 插件配置通过 `config.schema.json` 声明，由 Registry 校验。

### 默认值与校验

- 默认值必须支持最小启动：`DATABASE_URL` 允许为空时，相关功能可以降级而非崩溃。
- 配置校验在启动时执行，不在运行时每次读取。
- 环境变量缺失时的错误信息必须清晰但不泄密（不暴露完整连接串或路径）。

### Secret 管理

- Secret 只存 reference（如环境变量名或 vault 路径），不存明文。
- 日志、错误响应和测试 fixture 禁止打印 secret 值。
- 插件配置中的敏感字段在 schema 中标记 `sensitive: true`，API 返回时遮盖。

### 测试中的配置

- 测试 fixture 不使用真实 secret 或外部服务地址。
- 测试配置与生产配置分离。
- 环境变量在 fixture 中显式设置，不依赖宿主环境。

## 并发与幂等

### 并发保护

- ORM 写操作涉及共享状态时，必须使用乐观锁（version field）或悲观锁（`SELECT ... FOR UPDATE`）。
- 插件执行超时后不能留下不确定状态；必须有 cleanup 和状态回滚。
- 事件发布必须考虑顺序性和幂等性。

### 幂等性

- 插件调用必须可安全重试；重试不产生重复副作用。
- 事件处理必须天然幂等或通过 dedup key 保证。
- 幂等策略必须注释说明：`# 幂等：相同 request_id 返回缓存结果，不重复执行`

### 测试要求

- 并发场景必须有测试：`asyncio.gather` 模拟并发写入。
- 幂等性必须有测试：相同请求重复调用，验证结果不变。
- 超时降级必须有测试：mock 慢响应，验证超时后状态正确。

## 跨模块调用

### 调用方向规则

- `apps/api` → `packages/core`：允许，通过 core 的公开 API。
- `packages/core` → `packages/plugin-sdk`：允许，使用 SDK 定义的 Protocol 和 DTO。
- `plugins/*` → `packages/plugin-sdk`：允许，只通过 SDK 定义的接口。
- `plugins/A` → `plugins/B`：**禁止**，通过事件或 core 中介。
- `packages/core` → `apps/api`：**禁止**，是 `must-fix`。
- `packages/core` → `plugins/*`：**禁止**直接 import，通过 Registry 抽象。

### 接口隔离

- `RuntimePlugin` Protocol 保持最小：只定义必要的方法（`load`、`start`、`stop`、`health_check`）。
- 不强迫插件实现不需要的方法；不同类型插件可以有独立的 Protocol。
- Service 不依赖插件的内部实现细节，只依赖 SDK 定义的接口。

## 注释规范

与 API Architecture Gate 相同的注释要求，以下场景必须注释：

- **插件生命周期**：`# 加载顺序：先验证 manifest，再加载 entrypoint，最后注册能力`
- **状态流转**：`# 插件状态：discovered → validated → loaded → started，失败回退到 discovered`
- **隔离策略**：`# 同步插件通过 run_in_executor 执行，避免阻塞事件循环`
- **超时策略**：`# 插件执行超时 30s，超时后标记 failed 并触发通知，不等待 cleanup`
- **缓存失效**：`# 配置变更后失效 registry 缓存，下次查询重新加载`
- **安全校验**：`# entrypoint 路径校验：禁止 .. 穿越，禁止访问插件目录外文件`
- **刻意简单**：`# 未引入事件总线：当前只有同步调用场景，异步解耦在 v2 再引入`
- **依赖倒置**：`# service 依赖 repository Protocol，不依赖 SQLAlchemy session 实现`

注释应说明"为什么这样做"，不要复述代码在做什么。

## 规划和 Review 口径

- Issue / OpenSpec 规划阶段必须写清 package 边界、插件分层、DTO 契约、Registry 接口、数据流、失败路径和验证入口。
- PR 阶段必须说明实现是否遵循本 gate；偏离时说明原因、风险和后续收敛点。
- Code Review 阶段只对当前 diff 中新增或扩大债务的问题给 actionable finding；未触碰历史问题列 residual risk / defer。

`must-fix` 信号：

- `packages/core` 依赖 `apps/api`、FastAPI、React 或具体插件实现。
- API envelope、HTTP status code、前端展示逻辑进入 core。
- ORM model 直接作为 API DTO、Event DTO 或 Plugin DTO 返回。
- 插件之间互相 import，或插件直接 import core 内部实现。
- 状态流转覆盖历史记录而非 append-only。
- 审计和主表不在同一事务内写入。
- Registry 硬编码插件列表或 if-else 分发。
- `DATABASE_URL` 缺失导致 import 阶段崩溃（应延迟到使用时）。
- Alembic migration 历史被删除、重排或手改。
- 插件执行无超时保护，可无限阻塞。
- 插件返回值无大小限制，可能导致内存溢出。
- `except Exception: pass` 或空 `except` 块。
- 日志或错误响应暴露 secret、token 或数据库连接串。

`should-fix` 信号：

- Service 直接使用 ORM session 而非 repository 接口，但当前只有一个实现。
- Repository 接口过宽，包含当前不需要的方法。
- 插件 DTO 与 API DTO 混合在同一个 schema 文件中。
- 配置校验散落在多个地方而非集中处理。

`defer` / `residual risk` 信号：

- 历史代码已有但当前 PR 未触碰的不规范结构。
- 需要专门迁移 issue 才能解决的 package 边界问题。
- 缓存策略缺失但当前无性能瓶颈证据。
- 未引入事件总线但当前只有同步调用场景。

## 验收测试指导

### 测试层次与覆盖要求

Core 和 Plugin 变更必须有匹配的测试覆盖。按变更风险选择最小有效测试层次：

| 变更类型 | 必须覆盖 | 建议覆盖 |
| --- | --- | --- |
| 新增 / 修改 Registry 扫描或校验 | manifest 发现 + 校验规则 + 错误状态 | 重复 ID、路径穿越、缺失字段 |
| 新增 / 修改 RuntimeService 加载 | 插件加载 + 启动 + 停止 + 健康检查 | 加载失败隔离、超时降级 |
| 新增 / 修改 ORM model | 字段映射 + 约束 | 关系加载（N+1）、索引覆盖 |
| 新增 / 修改 repository | CRUD 基本路径 + 查询条件覆盖 | 批量操作、软删除过滤、分页边界 |
| 新增 / 修改插件 DTO | 序列化 / 反序列化 + 校验规则 | 边界值、大小限制 |
| 新增 / 修改 plugin-sdk Protocol | 接口契约测试 | 插件不实现不需要的方法 |
| 新增插件 | 插件功能测试 + config schema 校验 | 错误路径、超时、资源限制 |
| 数据库 migration | `upgrade` + `downgrade` 可执行 | 数据 backfill 正确性 |
| 并发 / 异步相关 | 竞态条件 + 幂等性 | 超时降级、资源限制 |

### 测试编写原则

- **测试行为，不测实现**：验证 registry 返回正确的插件记录，不验证内部扫描了哪些目录。
- **每条测试只验证一个行为**：一个 test 方法只 assert 一个关注点。
- **mock 边界要准**：只 mock 外部边界（文件系统、网络、DB），不 mock 同层依赖。
- **插件测试要隔离**：每个插件测试使用独立的 mock RuntimeContext，不共享状态。
- **失败路径必须测**：manifest 缺失字段、entrypoint 加载失败、插件执行超时、secret 未配置等场景。
- **不使用真实 secret 或外部服务**：测试 fixture 中用 mock 替代真实 API key、数据库连接和外部 HTTP 调用。

### 插件测试组织

```text
plugins/sources/<plugin-name>/
  tests/
    test_<plugin-name>.py       # 功能测试
    test_<plugin-name>_config.py  # config schema 校验（如果配置较复杂）
```

- 每个插件至少有一个测试文件验证核心功能。
- 插件测试既验证插件自身逻辑，也验证与 SDK Protocol 的兼容性。

### 验证命令

```bash
cd packages/core && uv run python -m unittest discover -s tests
cd plugins/sources/<plugin-name> && uv run python -m unittest discover -s tests
```

完成后说明改了哪些文件，以及实际跑过哪些验证；如果因为环境缺失无法验证，要明确说明缺口。

## 文档回写规则

对系统架构、平台能力、插件契约或工程规范有影响的变更，必须及时回写对应文档。

### 回写判断

| 变更场景 | 回写目标 | 优先级 |
| --- | --- | --- |
| 新增 / 修改 ORM model 或表结构 | `packages/core/AGENTS.md`、`docs/design/04-database-and-persistence-design.md` | 高 |
| 新增 / 修改 Registry 接口或扫描规则 | `packages/core/AGENTS.md`、`docs/design/03-plugin-system-and-registry.md` | 高 |
| 新增 / 修改插件类型、DTO 或 Protocol | `packages/plugin-sdk/AGENTS.md`、`plugins/AGENTS.md`、`docs/design/03-plugin-system-and-registry.md` | 高 |
| 修改 package 依赖方向或新增 package | 根 `AGENTS.md` 项目边界、`docs/design/01-tech-stack-and-project-structure.md` | 高 |
| 修改插件生命周期、执行隔离或超时策略 | `plugins/AGENTS.md`、本 gate 文件 | 高 |
| 修改配置加载、Secret 管理或环境变量 | `packages/core/AGENTS.md` 配置节 | 中 |
| 新增或修改共享 service / repository 模式 | `packages/core/AGENTS.md`、本 gate 文件 | 中 |
| 局部 bug 修复或纯实现细节调整 | 通常不需要回写 | 低 |

### 回写原则

- **按具体实例判断**：只回写对后续开发和协作有长期影响的规则和约定。
- **回写最小有效范围**：只补充或修正受影响的部分，不重写整篇文档。
- **PR 中说明回写**：列出更新了哪些文档以及原因；如果判断不需要回写，也要说明理由。
- **不要过度回写**：一次性实现细节、临时 workaround、未确认的想法不回写到长期文档。
- **gate 文件和 AGENTS.md 互补**：gate 定义目标架构和审查口径，AGENTS.md 记录当前约定和行为约束。两者不要重复。
