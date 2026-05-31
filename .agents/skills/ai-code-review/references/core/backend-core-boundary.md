# Core 后端边界审查

本文件用于审查 `packages/core` 中共享基础设施、配置、Event Bus、数据库、状态审计和运行时端口相关变更。它是当前 core 后端 CR 的最小闭环细则，后续可按 #168 继续拆成 package boundary、config、db、registry、events、secrets、tests 等专题。

## 适用范围

触发信号：

- 修改 `packages/core/src/quantagent/core/**`、`packages/core/pyproject.toml`、`packages/core/alembic/**`、`packages/core/tests/**`。
- 新增 Event Bus、publisher / consumer port、codec、Kafka adapter、memory fake、handler registry、settings、repository / storage port、registry 或 runtime service。
- core 变更同时影响 API、worker、scheduler、Docker、`.env.example` 或设计文档。

## 目标规范

- `packages/core` 是共享基础设施包，不依赖 FastAPI、React、具体 app 入口或具体插件实现。
- Core 不写 API envelope、HTTP status、前端展示逻辑、route 行为或 app 私有鉴权。
- 新共享能力必须有真实复用方、稳定职责和依赖方向；不要为了“以后可能会用”提前创建大而空的框架。
- Event Bus V1 进入 core 时，调用方依赖 publisher / consumer / handler registry port，不直接耦合 Kafka client。
- 内存 fake 与 Kafka adapter 必须共享同一 `EventEnvelope`、topic policy、codec 和错误语义；测试默认不依赖 Kafka。
- Event Bus 不替代数据库、REST、audit、outbox、replay 或 DLQ 真源；V1 如不做持久化，README / design / tests 必须说清边界。
- Plugin SDK / RuntimeContext 不暴露 event bus publisher、DB session、scheduler、internal service 或 secret resolver；插件输出由平台 service 转换后发布。
- 配置默认值支持最小启动；只有显式选择 Kafka backend 时才要求 Kafka 配置可用。
- Secret、token、连接串、私有策略、完整 prompt 和敏感工具参数不得进入日志、错误、headers、payload 快照或测试断言。
- 状态流转、Decision、Approval、Audit 等关键状态后续必须 append-only 可回放；当前 Event Bus 只做分发时不得伪装成审计真源。

## 审查步骤

1. 检查 imports 和依赖：core 是否引入 FastAPI、apps、web、具体插件或 API envelope。
2. 检查目录职责：model、ports、codec、topics、memory fake、Kafka adapter、service、config、README 是否按职责拆分。
3. 检查 `EventEnvelope` 是否是跨 backend 的稳定 contract，是否包含 id、topic、payload、producer、created_at、correlation / causation、headers、retry、schema_version 等关键语义。
4. 检查 topic policy 是否统一验证命名、prefix 和版本，不由调用方随意拼字符串。
5. 检查 handler registry 是否隔离 handler dispatch、错误分类、重试语义和订阅生命周期。
6. 检查 Kafka adapter 是否只在显式 backend 下加载/连接；缺配置时是否清晰失败且脱敏。
7. 检查 memory fake 是否能覆盖无 Kafka contract tests，是否避免把测试变成依赖外部 broker。
8. 检查 README / 中文注释是否说明插件隔离、持久化非目标、offset / retry / shutdown 等非显然取舍。

## Must-fix

- Core 依赖 `apps/api`、FastAPI、React、具体插件实现、API envelope 或 HTTP status。
- 调用方需要直接 import Kafka client 才能发布/消费事件，绕过 core port。
- `EVENT_BUS_BACKEND=memory` 或默认配置仍要求 Kafka broker / bootstrap servers，导致普通本地启动或单元测试失败。
- Kafka adapter 在 import settings、创建 app 或导入模块时就连接 broker，而不是在显式 factory / lifespan / composition root 中连接。
- Event Bus publisher 暴露给 Plugin RuntimeContext，或插件可以绕过平台 service 自行发布消息。
- 错误、日志、headers、payload 或测试快照泄露 secret、连接串、token、cookie、私有策略或完整 prompt。
- Event Bus 代码声称提供业务状态恢复、审计、replay 或 DLQ，但没有数据库 / audit / outbox 边界和验证。

## Should-fix

- Event Bus 目录有基础文件拆分，但 README 没写清谁可以调用 publisher、谁只能实现 handler、哪些对象不能放入 envelope。
- Kafka retry / commit / shutdown 语义在代码中可推断，但缺少中文注释说明取舍。
- Topic 常量可用，但缺少负例测试覆盖非法 topic、空 producer、schema_version 缺失等 contract。
- 新增环境变量已进入 settings，但 Docker、`.env.example` 或 README 未同步到足够可操作。

## 常见误判

- Kafka adapter 可以暂时放在 core 内部，只要调用方依赖 core port；是否未来拆到 adapters 是后续边界，不是当前 must-fix。
- V1 不实现 outbox、replay、DLQ 数据库记录可以接受，但必须明确非目标，不能暗示已具备可靠恢复。
- Handler registry 作为测试 fake 和未来 worker composition root 的接缝是合理抽象；问题在于无调用方的大而空框架。
- Memory fake 不是低质量实现；它是本地开发和 contract test 的目标 backend。

## Good example

```py
class EventPublisher(Protocol):
    async def publish(self, envelope: EventEnvelope) -> PublishResult: ...


def create_event_bus(settings: EventBusSettings) -> EventBus:
    if settings.backend == "memory":
        return MemoryEventBus()
    if settings.backend == "kafka":
        return KafkaEventBus.from_settings(settings)
    raise EventBusConfigurationError("Unsupported event bus backend")
```

调用方依赖 core port，Kafka 只在显式 backend 下创建。

```py
@dataclass(frozen=True)
class EventEnvelope:
    id: str
    topic: str
    payload: Mapping[str, Any]
    producer: str
    created_at: datetime
    correlation_id: str | None = None
    causation_id: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    retry_count: int = 0
    schema_version: str = "v1"
```

Envelope 表达分发协议，不冒充 ORM、API DTO 或审计记录。

## Bad example

```py
from fastapi import HTTPException

class EventBusError(HTTPException):
    status_code = 503
```

问题：core 错误耦合 HTTP 语义。

```py
class RuntimeContext:
    event_bus: EventPublisher
    db_session: Session
```

问题：插件上下文暴露内部 publisher 和 DB session，插件可绕过平台 service、审计和策略边界。

```py
settings = EventBusSettings()
producer = KafkaProducer(settings.bootstrap_servers)
```

问题：模块导入即连接 Kafka，破坏最小启动和测试 fake。

## 验证建议

- Core contract tests：运行 `packages/core` 相关 event bus 单元测试，覆盖 envelope、topic、codec、memory fake、handler dispatch 和错误路径。
- Kafka adapter：用显式环境开关运行 integration / smoke；未启动 Kafka 时应清晰 skip，并在最终说明写明。
- 配置与 Docker：从仓库根目录验证 compose 配置可解析；确认默认 `.env.example` 不要求真实 Kafka secret。
- 脱敏：人工或测试检查错误、日志、headers、payload 和 test snapshot 不包含 secret / token / 连接串原文。
