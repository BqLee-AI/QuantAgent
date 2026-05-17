# Tasks: 收住 apps/api v1 路由与契约骨架

## 状态

实现任务已完成，当前状态为等待最终人工审核与归档确认。

## 任务图

### 阻塞串行路径

- [x] B0. 实现前审核 OpenSpec artifacts
  - 输入：issue #60、`proposal.md`、本 `tasks.md`、spec delta
  - 输出：维护者明确批准进入实现
  - 写入边界：无
  - 阻塞原因：本 workflow 要求先产出可持久化审核的 spec artifact，再改应用代码

- [x] B1. 稳定 API v1 注册方式与目录边界
  - 输入：`apps/api/src/quantagent/api/main.py`、现有 `routers/health.py`、现有 `routers/debug.py`、`apps/api/src/quantagent/api/db.py`
  - 输出：共享 API v1 router 注册 helper `register_api_v1_routes`；常规 router 与 debug-only router 的清晰加载路径；`routers/`、`schemas/`、`providers/` package 边界；现有 FastAPI lifespan 数据库初始化/释放路径不被改坏
  - 写入边界：`apps/api/src/quantagent/api/main.py`、`apps/api/src/quantagent/api/routers/**`、`apps/api/src/quantagent/api/schemas/**`、`apps/api/src/quantagent/api/providers/**`
  - 依赖：B0

- [x] B2. 新增非业务 `version` 示例资源
  - 输入：B1 注册 helper、`ApiResponse[T]`、issue #60 的命名约束
  - 输出：`GET /api/v1/version`、`schemas/` 下的响应 DTO（仅含 `service`、`api_version`、`version`）、`providers/` 下的 sample provider、显式 `response_model`、显式 tags
  - 写入边界：`apps/api/src/quantagent/api/routers/**`、`apps/api/src/quantagent/api/schemas/**`、`apps/api/src/quantagent/api/providers/**`
  - 依赖：B1

- [x] B3. 将现有 health/ready 探针 route 纳入同一显式契约
  - 输入：`routers/health.py`、`ApiResponse[T]`、`get_db_session`、OpenAPI 预期、PR #70 的 readiness 行为
  - 输出：`/api/v1/health` 保持 liveness 响应体；`/api/v1/ready` 保持数据库 readiness 语义和 503 envelope；两者都暴露显式 `response_model` 和 tags
  - 写入边界：`apps/api/src/quantagent/api/routers/health.py`
  - 依赖：B1

### B1 后可并行任务

- [x] P1. 增加 API route 与 OpenAPI 契约测试
  - 输入：B1 helper 行为、B2/B3 route 契约、现有 `src/tests/test_app.py`
  - 输出：覆盖 `/api/v1/version`、`/api/v1/health`、`/api/v1/ready`、OpenAPI path/tag/schema 可见性、envelope shape、production debug route exclusion 的测试；保留现有 readiness 未配置/失败/成功与 DB session dependency 覆盖
  - 写入边界：`apps/api/src/tests/**`
  - 可与 P2 并行：route 契约名称稳定之后

- [x] P2. 文档化 API v1 router 新增流程
  - 输入：B1 目录/注册 helper、B2 sample provider 边界、PR #70 已有数据库 readiness 说明、本 proposal 的非目标
  - 输出：`apps/api/README.md` 说明新增 API v1 router、schema、provider、tags、`response_model`、测试要求、最小验证命令和非目标；区分 sample provider 与已有 DB session dependency
  - 写入边界：`apps/api/README.md`
  - 可与 P1 并行：route 契约名称稳定之后

- [x] P3. 在 README 中加入 API 包最小验证命令
  - 输入：当前 Python 测试布局与本 change 的契约测试要求
  - 输出：`apps/api/README.md` 明确记录 `cd apps/api && uv run python -m unittest discover -s src/tests`
  - 写入边界：`apps/api/README.md`
  - 可与 P2 合并执行：两者写入同一文件，实际实现时应由同一人处理以避免冲突

### 审核检查点

- [x] R1. 确认 sample resource 命名和 payload 不暗示 runtime、metadata、plugin、approval、Agent、tool invocation、WebSocket、executor 或 live trading 能力。
- [x] R2. 确认 provider/sample data 只表达替换点，不包含数据库访问、核心领域逻辑、runtime health state、registry state、credentials 或外部服务调用。
- [x] R3. 确认 production app 和 production OpenAPI schema 都排除 debug-only routes。
- [x] R4. 确认 README 不声称 API resources、OpenAPI artifacts、generated clients 或业务 endpoint families 已完成。
- [x] R5. 确认 README 的最小验证命令能作为后续新增 API route 的默认本地验证入口。
- [x] R6. 确认 router 注册 helper、显式 `response_model` 和测试调整没有破坏 PR #70 已有 `/api/v1/ready` readiness 行为、503 envelope、敏感信息不泄露和 lifespan 资源清理。

## 验证任务

- [x] V1. 运行 API 测试：`cd apps/api && uv run python -m unittest discover -s src/tests`
- [x] V2. 验证 OpenSpec change：`openspec validate api-v1-route-contract-skeleton --type change --strict --json`

## 说明

- 实现路径在 B1 前基本串行，因为 route 注册、package 边界和 FastAPI lifespan 保护是共享写入区域。
- B1 之后测试与 README 更新可以并行，因为它们写入边界不同；P2 与 P3 都写 README，实际实现时应合并在同一编辑中完成。
