# AGENTS.md

## 定位

- `packages/core` 是 QuantAgent 的共享基础设施包。
- 当前职责包括通用配置、数据库 engine/session、SQLAlchemy Base 和 Alembic 迁移入口。
- 这里可以承载未来被 API、worker、scheduler 和插件共同依赖的领域基础能力。

## 行为约束

- 不依赖 FastAPI、React、具体 app 入口或具体插件实现。
- 不在 core 中写 API 响应结构、HTTP 状态码或前端展示逻辑。
- core runtime 只能基于 Registry record 和 manifest entrypoint 加载插件，不能维护第二套插件发现或硬编码注册入口。
- 插件 RuntimeContext 是受控上下文，不作为服务定位器；默认不得暴露 DB session、ORM model、scheduler、Event Bus publisher、内部 service 或 secret resolver。
- API router 不承载插件 entrypoint 加载、生命周期托管或 invoke 编排；这些能力应留在 core runtime 或后续明确的 runtime service 边界。
- 配置默认值应支持最小启动，不用无关配置阻塞只需要部分能力的场景。
- `DATABASE_URL` 允许为空；只有创建数据库 engine 或执行迁移时才要求存在。
- Alembic 配置和迁移历史不能随意删除、重排或改写。
- Event 是核心运行时主对象；事件状态流转、插件状态、Decision、Approval 和 Audit 等关键状态需要支持回放。
- ORM model 只负责数据库映射，不直接作为 API DTO、Event DTO 或 Plugin DTO 使用。
- 插件不能直接持有数据库 session；后续应通过 repository、storage port 或 RuntimeContext 访问持久化能力。
- 审计和状态流转类数据按 append-only 思路设计，不为省事覆盖历史。
- 不默认保存完整模型推理链、secret、私有策略或敏感工具参数。
- 共享能力必须有清晰职责和调用方；只有被 API、worker、scheduler、插件或其他 package 复用的基础能力才进入 core。
- 涉及数据库写入、状态机、审计、插件运行时或外部端口时，优先用 service/repository/port 等边界表达职责，避免把持久化、校验和领域流程混在 ORM model 或散落函数里。
- Repository / storage port 的引入必须服务真实持久化、跨模块复用或插件隔离需求；不为“以后可能会用”提前设计完整框架。

## 局部规则

- 涉及 `packages/core/**` 的规划、实现和 review 必须读取 `.agents/skills/references/core-and-plugin-architecture-gate.md`，把目标分层落实到 issue、OpenSpec、实现计划或 PR 说明。
- 新增共享配置时先判断是否真的跨 app/package 复用；API 私有项保留在 `apps/api`。
- 新增数据库能力时优先放在 `src/quantagent/core/db/`，并补充 `packages/core/tests/`。
- 修改迁移加载或数据库 URL 逻辑时，同时检查 `packages/core/alembic.ini` 和 `packages/core/alembic/env.py`。
- 如果实现结果改变 `docs/design/04-database-and-persistence-design.md` 中的持久化边界，需要在 PR 说明证据并回写设计或 OpenSpec。
