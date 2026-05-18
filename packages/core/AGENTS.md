# AGENTS.md

## 定位

- `packages/core` 是 QuantAgent 的共享基础设施包。
- 当前职责包括通用配置、数据库 engine/session、SQLAlchemy Base 和 Alembic 迁移入口。
- 这里可以承载未来被 API、worker、scheduler 和插件共同依赖的领域基础能力。

## 行为约束

- 不依赖 FastAPI、React、具体 app 入口或具体插件实现。
- 不在 core 中写 API 响应结构、HTTP 状态码或前端展示逻辑。
- 配置默认值应支持最小启动，不用无关配置阻塞只需要部分能力的场景。
- `DATABASE_URL` 允许为空；只有创建数据库 engine 或执行迁移时才要求存在。
- Alembic 配置和迁移历史不能随意删除、重排或改写。
- Event 是核心运行时主对象；事件状态流转、插件状态、Decision、Approval 和 Audit 等关键状态需要支持回放。
- ORM model 只负责数据库映射，不直接作为 API DTO、Event DTO 或 Plugin DTO 使用。
- 插件不能直接持有数据库 session；后续应通过 repository、storage port 或 RuntimeContext 访问持久化能力。
- 审计和状态流转类数据按 append-only 思路设计，不为省事覆盖历史。
- 不默认保存完整模型推理链、secret、私有策略或敏感工具参数。

## 局部规则

- 新增共享配置时先判断是否真的跨 app/package 复用；API 私有项保留在 `apps/api`。
- 新增数据库能力时优先放在 `src/quantagent/core/db/`，并补充 `packages/core/tests/`。
- 修改迁移加载或数据库 URL 逻辑时，同时检查 `packages/core/alembic.ini` 和 `packages/core/alembic/env.py`。
- 如果实现结果改变 `docs/design/04-database-and-persistence-design.md` 中的持久化边界，需要在 PR 说明证据并回写设计或 OpenSpec。
