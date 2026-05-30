# API 后端边界审查

本文件用于审查 `apps/api` 中 FastAPI 入口、生命周期、配置接入、readiness、错误与运行时集成相关变更。它是当前 API 后端 CR 的最小闭环细则，后续可按 #167 继续拆成 router、DTO、auth、db、debug 等专题。

## 适用范围

触发信号：

- 修改 `apps/api/src/quantagent/api/main.py`、`db.py`、`routers/**`、`http/**`、`schemas/**`、`auth/**`。
- 新增或调整 API app factory、lifespan、route registration、readiness / health、debug route、request id、错误处理。
- API 入口接入 Event Bus、Registry、worker、scheduler、Kafka、数据库或其他长期运行时能力。

## 目标规范

- `apps/api` 是 HTTP/API 传输层，只处理 HTTP 参数、DTO、状态码、响应信封、依赖注入、异常映射、路由注册和应用生命周期挂载。
- Router 保持薄层；业务流程、状态变化、插件生命周期、审计、数据库写入、外部适配和高风险动作必须进入 service/provider/repository/port 边界。
- 标准 API v1 routes 统一通过 `register_api_v1_routes` 注册，避免在 `main.py` 零散堆叠业务 router。
- API 可以在 lifespan 初始化共享基础设施，但不启动长期 consumer loop、scheduler loop 或后台事件处理；长期 consumer / handler composition root 属于 worker / scheduler 边界。
- `GET /api/v1/health` 不依赖数据库或外部服务；`GET /api/v1/ready` 只验证明确的 readiness 依赖，并返回统一 envelope / request id。
- API DTO、ORM model、Event DTO、Plugin DTO 和响应 envelope 分层独立；公开响应长期使用 `ApiResponse[T]`。
- Debug route 只用于非生产诊断，生产环境不可见，生产 OpenAPI 不暴露 debug path。
- 错误响应不得泄露 secret、连接串、token、cookie、完整 traceback、完整 prompt 或私有策略。
- 新增环境变量、Docker 入口或 readiness 依赖时，同步检查 `.env.example`、`apps/api/.env.example`、README / design 是否一致。

## 审查步骤

1. 找出 API 入口是否只做 app factory、middleware、exception handler、lifespan 和 route registration。
2. 检查新增 runtime 能力是在 API lifespan 中做一次性初始化，还是启动了长期循环、consumer 或后台任务。
3. 检查 router 是否返回 `ApiResponse[T]`，是否返回 ORM / 裸 dict / 内部 EventEnvelope。
4. 检查 health / ready 是否区分 liveness 与 readiness，失败是否结构化且脱敏。
5. 检查 request id 是否贯穿响应头与错误体，异常处理是否仍走 `AppError` / 统一 handler。
6. 检查 debug / env / OpenAPI 在 production 下是否隐藏敏感诊断能力。

## Must-fix

- 在 FastAPI router 或 `main.py` 中启动长期 Kafka consumer、scheduler loop、worker loop 或业务 handler dispatch。
- Route 内直接创建数据库 engine/session、commit 状态变化、扫描插件、调用 Agent workflow 或承载多步骤业务流程。
- 新增公开 API 返回 ORM model、裸 dict、内部 EventEnvelope 或绕过 `ApiResponse[T]` 的长期契约。
- `health` 依赖数据库、Kafka 或外部服务；`ready` 失败泄露连接串、Kafka broker、token、traceback 或 secret。
- Debug route 在 `APP_ENV=production` 下可见，或生产 OpenAPI 暴露 debug path。
- API 错误吞掉 request id，或把底层异常原文直接返回给前端。

## Should-fix

- `main.py` 只新增少量基础设施 wiring，但没有中文注释说明为什么该能力只在 lifespan 挂载且不承担长期 consumer。
- 新增环境变量已可运行，但 `.env.example`、API README 或部署说明没有同步。
- readiness 只覆盖 happy path，缺少依赖不可用、配置缺失或关闭功能开关的测试。

## 常见误判

- API lifespan 可以初始化共享 client、检查配置或挂载 app state；问题在于让 API 承担长期消费和业务调度。
- `health` 返回简单数据是合理的，不需要强行抽 service。
- 骨架期 sample provider 可以保留，但不能被扩展成真实业务流程或持久化服务。
- 只改旧路由文案或示例字段时，不要求顺手重构整个 API 层；但新增行为必须按目标边界收敛。

## Good example

```py
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.event_bus_factory = build_event_bus_factory(settings)
    yield
    await app.state.event_bus_factory.close()
```

API 只挂载可复用基础设施生命周期，不启动长期 consumer。

```py
@router.get("/ready", response_model=ApiResponse[ReadinessResponse], tags=["runtime"])
def ready(db: Session = Depends(get_readiness_session)):
    return ApiResponse.success(ReadinessResponse(database="ok"))
```

readiness 只表达依赖是否可用，并保持 envelope。

## Bad example

```py
@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = KafkaConsumer(...)
    consumer.subscribe("source.event.captured", handle_event)
    await consumer.run_forever()
    yield
```

问题：API 进程承担长期 consumer loop，阻塞或污染 HTTP 生命周期，也违反 worker / scheduler composition root 边界。

```py
@router.post("/plugins/{plugin_id}/enable")
def enable_plugin(plugin_id: str, db: Session = Depends(get_db_session)):
    record = db.query(PluginRecord).filter_by(id=plugin_id).one()
    record.status = "enabled"
    db.commit()
    return record
```

问题：router 承载持久化和插件生命周期，返回 ORM，绕过 envelope 和审计。

## 验证建议

- API 行为：`cd apps/api && uv run python -m unittest discover -s src/tests`
- Docker / env / readiness：从仓库根目录验证 compose 配置可解析，并按改动说明是否实际启动服务。
- Event Bus 接入：确认 API 测试无需 Kafka；Kafka 只在显式配置或 profile 下启用。
