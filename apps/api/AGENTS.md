# AGENTS.md

## 定位

- `apps/api` 是 QuantAgent 的 FastAPI 服务入口，只负责 HTTP 边界。
- 这里可以放路由、请求生命周期、中间件、异常处理、依赖注入和 API 私有配置。
- 核心领域逻辑、共享数据库能力、跨应用配置和可复用基础设施应下沉到 `packages/core`。

## 行为约束

- 不在 API 层写需要被 worker、scheduler、插件或前端复用的核心逻辑。
- 不在路由里直接创建数据库 engine；使用应用生命周期和依赖注入管理连接。
- 不硬编码数据库地址、生产端口、secret 或部署环境值；通过 Settings 和环境变量读取。
- 生产环境不能暴露 debug-only 路由或调试响应。
- API 错误响应应保持结构稳定，不把底层异常、secret 或连接串原文返回给调用方。
- 新增业务 API 时遵守 `docs/design/08-api-and-websocket-design.md` 的资源边界：REST 资源为主，副作用操作放在资源下的 `actions` 路径。
- API DTO 必须独立于 ORM model，不能直接返回 SQLAlchemy model。
- HTTP API 应逐步收敛到 `code/data/msg/error` envelope；引入例外时必须在 PR 中说明原因和兼容策略。
- WebSocket 或实时通道只负责状态变化通知，不替代 REST 查询和数据库状态真源。
- 高风险动作即使来自前端按钮或 AI 文本，也必须经过后端 Policy Gate。

## 局部规则

- 新增路由时优先放在 `src/quantagent/api/routers/`，并在 `main.py` 中显式注册。
- 需要访问数据库时，优先复用 `quantagent.api.db` 中的 session 依赖。
- API 配置只保留服务入口私有项；能被其他 Python package 复用的配置放到 `packages/core`。
- 改动 API 行为时，同步补充或调整 `apps/api/src/tests/` 下的测试。
- 新增或修改跨前端契约时，需要关联 `packages/contracts`、OpenAPI 或 JSON Schema 的真源计划，不能只改临时返回字段。
