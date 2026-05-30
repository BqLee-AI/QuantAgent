# packages/core Review Overview

本文件是 `packages/core` 变更的 AI Code Review 索引。先用 changed files 和 diff 识别场景，再加载对应细则。

现有代码只能作为迁移背景，不是规范来源。审查新增或被修改代码时，以 `packages/core/AGENTS.md`、设计文档、OpenSpec 和共享基础设施目标分层作为边界；如果当前实现与目标边界冲突，按证据标为 finding 或 residual risk。

主要真源：

- `packages/core/AGENTS.md`
- `docs/design/01-tech-stack-and-project-structure.md`
- `docs/design/02-core-architecture-and-runtime.md`
- `docs/design/04-database-and-persistence-design.md`
- `.agents/skills/references/engineering-quality-gate.md`

## 场景索引

| 场景 | 触发信号 | 未来细则 | 核心审查问题 |
| --- | --- | --- | --- |
| Package 边界与依赖方向 | `packages/core/pyproject.toml`、core imports、新共享抽象 | `package-boundary-and-dependencies.md` | core 是否反向依赖 FastAPI、React、apps 或具体插件；新增共享能力是否有真实调用方 |
| Config / Settings | `core/config/**`、环境变量、默认值、secret 配置 | `config-and-settings.md` | 默认值是否支持最小启动；`DATABASE_URL` 是否允许为空；API 私有配置是否误下沉 core |
| DB session / Alembic | `core/db/**`、`alembic.ini`、`alembic/env.py`、`alembic/versions/**` | `db-session-and-alembic.md` | engine/session 是否集中；迁移历史是否被改写；缺少 DB URL 时错误是否清晰且不泄密 |
| ORM / Repository / Port | ORM model、repository、storage port、domain object、mapper | `orm-models-repositories-and-ports.md` | ORM 是否只做映射；是否被当 API/Event/Plugin DTO；repository/port 是否有真实持久化或复用需求 |
| Registry 与插件边界 | `core/registry/**`、manifest、扫描、registry service | `registry-and-plugin-boundary.md` | 插件是否通过 `plugin.yaml` 和 Registry 进入；core 是否硬编码具体插件 class/import/if-else |
| Event / State / Audit | Event、Decision、Approval、Audit、runtime error、state transition | `events-state-and-audit.md` | 状态流转是否 append-only 可回放；主表与 audit 是否同事务；是否保存完整推理链或敏感参数 |
| Secret 与敏感数据 | plugin config、secret reference、日志、audit payload、raw event、tool args | `secrets-and-sensitive-data.md` | 是否默认保存 secret reference；日志、错误、审计和测试快照是否脱敏 |
| 测试与迁移验证 | core config、db、registry、migration、model、repository 改动 | `tests-and-migrations.md` | 是否补 core 测试；migration 配置是否可加载；是否避免提交 runtime 数据和缓存 |

## 选择规则

- core 中出现 `fastapi`、HTTP status、API envelope、React、apps 或具体插件 import 时，必须审查 package 边界。
- 修改 Alembic 或 ORM 时，必须同时审查迁移、结构化字段、DTO 分层和敏感数据。
- 新增 repository / port 时，先确认真实持久化、跨模块复用或插件隔离需求；不要为了模式本身抽象。
- 修改 registry 时，必须检查是否保持 manifest / Registry 边界，而不是写死插件实现。

## 初始 finding 倾向

优先报告这些问题：

- `packages/core` 依赖 `apps/api`、FastAPI、React 或具体插件实现。
- API envelope、HTTP status、前端展示逻辑进入 core。
- `DATABASE_URL` 缺失导致导入 settings 或最小启动失败。
- Alembic migration 历史被删除、重排或手改。
- ORM model 直接作为 API DTO、Event DTO 或 Plugin DTO 返回。
- 审计和状态流转覆盖历史而不是 append-only。

## 已落地细则

- `backend-core-boundary.md`

其余场景暂时由 overview 索引收束；后续按 #168 继续拆细。
