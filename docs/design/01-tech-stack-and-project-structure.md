# 01. 技术栈与项目结构设计

## 文档状态

**状态**：草案 v0.2  
**范围**：技术栈选型、monorepo 结构、插件目录规划、跨语言契约边界  
**不包含**：具体功能模块架构、Agent 工作流细节、交易策略设计、数据库表结构

## 设计原则

- 以用户确认的技术栈为准，PRD 仅作为背景参考。
- 项目以 Python 为主，TypeScript 主要承担前端和类型消费。
- 从 0 到 1 阶段保持单体可运行，但目录边界要支持未来多容器和微服务拆分。
- 行业包、数据源、策略适配器、通知器、交易通道都按插件体系规划。
- 官方内置插件、第三方社区插件、私有插件和运行时安装插件需要分层管理。
- 敏感配置、私有策略、数据源关键词、交易密钥不进入 Git。

## 已确认技术栈

| 层级 | 选型 |
| --- | --- |
| 后端 API | FastAPI |
| Agent / Workflow | DeepAgents |
| 前端 | React + Vite |
| Python 包管理 | uv |
| 前端包管理 | bun |
| 仓库形态 | monorepo |
| 部署目标 | Docker 部署 |
| 数据库 | PostgreSQL |
| Python ORM | SQLAlchemy 2.x |
| 数据库迁移 | Alembic |
| 插件 manifest | `plugin.yaml` |
| 插件配置 schema | Zod authoring + JSON Schema runtime validation |
| 初版 Event Bus | 进程内实现 |
| 后续 Event Bus 演进 | Redis |
| 初版插件热重载 | 支持 |
| 前端插件配置 | 仅支持 schema 驱动表单 |

## 推荐总体结构

```text
QuantAgent/
  apps/
    api/
    web/
    worker/
    scheduler/

  packages/
    core/
    agent/
    plugin-sdk/
    adapters/
    contracts/
      openapi/
      schemas/
      zod/
      generated/
        typescript/
        python/
    prompts/

  plugins/
    sources/
    industries/
    strategies/
    notifications/
    brokers/

  runtime/
    plugins/
    config/
    data/
    logs/

  infra/
    docker/
    compose/
    migrations/

  design/
  docs/
  docker-compose.yml
  pyproject.toml
  package.json
  uv.lock
  bun.lock
```

## 应用层目录

### `apps/api`

FastAPI 主入口，负责 HTTP API、WebSocket、认证、管理端接口和插件管理接口。

建议职责：

- 暴露前端需要的 API。
- 提供 WebSocket 事件流。
- 提供插件安装、启停、配置、健康检查等管理接口。
- 调用 `packages/core` 和 `packages/agent`，不直接实现复杂业务逻辑。

### `apps/web`

React + Vite 前端管理台。

建议职责：

- 展示事件流、行业包、插件列表、Agent 状态、交易建议。
- 通过 contracts 生成的 TypeScript 类型和 API client 调用后端。
- 根据插件配置 schema 渲染配置表单。
- 不承载核心交易判断和行业推理逻辑。

### `apps/worker`

后台任务执行入口。

建议职责：

- 执行数据源抓取。
- 执行事件路由。
- 调用 Agent workflow。
- 处理插件任务、长耗时任务和异步队列。

从 0 到 1 阶段可以和 API 共用同一代码包，但运行入口需要独立，为未来拆容器预留边界。

### `apps/scheduler`

定时任务入口。

建议职责：

- 触发周期性 RSS 抓取。
- 触发 URL watcher。
- 触发行业包定时扫描。
- 管理任务频率和限流。

如果早期复杂度不高，可以先合并到 worker，但目录上建议保留。

## Python 包层目录

### `packages/core`

核心领域包，不依赖 FastAPI，不依赖具体插件实现。

建议包含：

```text
packages/core/
  pyproject.toml
  alembic.ini
  alembic/
    env.py
    script.py.mako
    versions/
      .gitkeep
  src/
    quantagent/
      core/
        config/
        db/
        events/
        registry/
        ports/
        factories/
        lifecycle/
        errors/
        observability/
```

Python import namespace 统一使用：

```python
from quantagent.core.config.settings import settings
from quantagent.core.db.base import Base
from quantagent.core.db.session import create_sync_engine
```

不使用 `quantagent_core` import namespace。

建议后续能力目录：

```text
quantagent/core/
  events/
  registry/
  ports/
  factories/
  lifecycle/
  config/
  errors/
  observability/
```

职责：

- 定义事件模型。
- 定义插件生命周期。
- 定义 registry。
- 定义 ports / adapters 抽象接口。
- 定义 factory 创建规则。
- 定义统一错误、日志、追踪和配置读取约定。

### `packages/agent`

Agent 和 workflow 包。

建议包含：

```text
quantagent/agent/
  workflows/
  router/
  debate/
  scoring/
  memory/
  prompts/
```

职责：

- 封装 DeepAgents workflow。
- 实现 Router Agent。
- 实现行业分析 Agent 编排。
- 实现 Internal Debate 和评分逻辑。
- 调用行业插件提供的能力，但不直接耦合具体行业实现。

### `packages/plugin-sdk`

插件开发 SDK。

建议包含：

```text
quantagent/plugin_sdk/
  base/
  context/
  decorators/
  manifests/
  config_schema/
  testing/
```

职责：

- 给官方、第三方、社区和私有插件提供统一开发接口。
- 提供插件基类、装饰器、上下文对象和测试工具。
- 定义插件 manifest 和配置 schema 规范。

### `packages/adapters`

官方可复用 adapter 集合。

职责：

- 提供通用 RSS adapter。
- 提供通用 URL watcher adapter。
- 提供通用 Readability/Jina link reader adapter。
- 提供通用交易所、通知、存储 adapter 的基础实现。

具体业务插件可以依赖这些 adapter，但核心包不反向依赖具体实现。

## 数据库与 ORM 选型

数据库和 ORM 属于基础技术栈，初版即需要确定，避免后续事件模型、插件配置和审计记录难以迁移。

### 选型

| 层级 | 选型 |
| --- | --- |
| 数据库 | PostgreSQL |
| Python ORM | SQLAlchemy 2.x |
| 迁移工具 | Alembic |

### 选择理由

- PostgreSQL 稳定，适合事件、配置、审计、插件 registry 等结构化数据。
- SQLAlchemy 2.x 是 Python 生态成熟的 ORM 选择，适合 FastAPI 项目。
- Alembic 是 SQLAlchemy 生态常用迁移工具，方便版本化数据库结构。

### ORM 使用边界

- ORM model 只负责数据库映射。
- API DTO、Event DTO、Plugin DTO 不直接复用 ORM model。
- 领域层通过 repository 或 storage port 访问数据库。
- 插件不应直接持有数据库 session，应该通过上下文提供的 storage 接口读写。

## 插件目录设计

### 插件类型

| 类型 | 目录 | 示例 |
| --- | --- | --- |
| 数据源插件 | `plugins/sources/` | RSS、URL watcher、X API、Readability/Jina link reader |
| 行业包插件 | `plugins/industries/` | Oil、Semiconductor、Memory |
| 策略插件 | `plugins/strategies/` | 趋势策略、事件冲击策略、期权策略 |
| 通知插件 | `plugins/notifications/` | Discord、Telegram、Email |
| 交易通道插件 | `plugins/brokers/` | 美股券商、NYSE 相关接口、Binance、OKX |

### 行业包也是插件

行业包应统一纳入插件体系。一个行业包可以声明依赖多个前置数据源插件，也可以声明自己的 Agent、评分规则、市场映射和 broker 偏好。

例如石油行业包可以声明：

```text
Oil Industry Plugin
  depends_on:
    - source:x_api
    - source:rss
    - source:url_watcher
  agents:
    - oil_event_router
    - oil_supply_demand_analyst
    - geopolitical_risk_analyst
  markets:
    - us_equity
    - futures
    - crypto_proxy
  brokers:
    - broker:us_broker
    - broker:binance
    - broker:okx
```

### 官方插件与运行时插件

```text
plugins/
  sources/
  industries/
  strategies/
  notifications/
  brokers/

runtime/
  plugins/
```

约定：

- `plugins/` 存放官方出厂自带插件，可以进入 Git。
- `runtime/plugins/` 存放运行时安装的第三方、社区或私有插件，默认不进入 Git。
- 私有交易策略、敏感数据源关键词、未公开行业逻辑不应放入官方插件目录。
- 后端 registry 同时扫描官方插件目录和运行时插件目录。
- 运行时插件需要支持从 Git URL、本地 zip、私有目录三种方式导入。
- 官方插件使用独立命名空间，避免与社区和私有插件冲突。
- 初版支持插件热重载，用于安装、卸载、启停和配置变更后重新加载插件。
- 初版暂不引入插件签名校验、来源白名单和外部 Secret Manager。
- 插件必须具备版本管理，官方插件和运行时插件都需要声明版本。

命名空间建议：

| 来源 | 命名空间示例 |
| --- | --- |
| 官方插件 | `quantagent.official.source.rss` |
| 社区插件 | `community.<author>.<plugin>` |
| 私有插件 | `private.<org>.<plugin>` |
| 本地实验插件 | `local.<name>` |

## 插件 manifest 建议

每个插件建议包含一个 manifest 文件，用于注册和管理。

```text
plugin.yaml
src/
config.schema.ts
config.schema.json
README.md
tests/
```

建议字段：

```yaml
id: quantagent.official.industry.oil
name: Oil Industry Package
type: industry
version: 0.1.0
entrypoint: oil_plugin:plugin
permissions:
  - network
  - market_data
dependencies:
  plugins:
    - quantagent.official.source.x_api
    - quantagent.official.source.rss
config_schema: config.schema.json
capabilities:
  - event_analysis
  - scoring
  - strategy_mapping
```

版本管理要求：

- 每个插件必须声明 `version`。
- 插件升级、降级、启用、停用、卸载需要记录操作日志。
- Registry 需要能识别同一插件 ID 的当前版本。
- 初版不要求实现复杂依赖解析，但需要在 manifest 中保留依赖版本约束字段的扩展空间。

## Registry、Factory、Adapter、Event Bus

建议采用市面上常见插件型项目的组合模式：

- `Registry`：负责发现、注册、查询、启停插件。
- `Factory`：根据插件 manifest、配置和上下文创建具体实例。
- `Adapter / Port`：定义核心系统调用外部能力的稳定接口。
- `Event Bus`：让数据源、行业包、Agent、通知器、交易通道通过事件解耦。

核心流程：

```text
Plugin Discovery
  -> Manifest Validation
  -> Registry Registration
  -> Config Validation
  -> Factory Instantiation
  -> Lifecycle Start
  -> Event Bus Subscription
```

这样设计的原因：

- FastAPI 不需要知道每个插件的具体类。
- 行业包可以组合多个数据源插件。
- 同一个事件可以广播给多个行业包。
- 后续拆成微服务时，Event Bus 可以从进程内实现替换为 Redis、NATS、Kafka 等消息系统。
- 第三方插件可以通过 SDK 接入，而不是修改核心代码。

### 初版 Event Bus 选择

初版使用进程内 Event Bus。原因是 0 到 1 阶段更容易调试，部署依赖更少，也能更快验证插件生命周期、行业包路由和 Agent workflow。

设计时需要保留消息总线接口，避免业务代码直接依赖进程内实现。后续需要多容器或微服务化时，可以将实现替换为 Redis Streams，再根据吞吐和可靠性需求评估 NATS 或 Kafka。

## 跨语言共享边界

Python 和 TypeScript 不直接共享业务代码，只共享契约。

```text
packages/contracts/
  openapi/
  zod/
  schemas/
    events/
    plugins/
    configs/
    markets/
  generated/
    typescript/
    python/
```

共享内容：

- OpenAPI 接口定义。
- 事件 JSON Schema。
- 插件 manifest schema。
- 插件配置 schema。
- 市场、交易通道、行业包等枚举定义。
- 生成给前端使用的 TypeScript 类型和 API client。

### Zod 与 Python 的边界

插件配置 schema 采用 Zod 作为开发侧主入口，因为前端可以直接使用 Zod schema 做类型推导、表单校验和配置编辑体验。

运行时跨语言校验不直接依赖 Zod。约定流程如下：

```text
Zod Schema
  -> JSON Schema
  -> Python jsonschema / pydantic validation
  -> Registry accepts config
```

原因：

- Zod 是 TypeScript-first，适合前端和插件开发体验。
- Python 后端不应直接执行 TypeScript schema。
- JSON Schema 是跨语言契约，Python、TypeScript 和文档都能消费。
- Zod 4 支持导出 JSON Schema，适合承担 schema authoring 层。

约定：

- `config.schema.ts` 是插件配置 schema 的开发源。
- `config.schema.json` 是运行时产物，供 Python 后端校验。
- 官方插件必须提交两者。
- 第三方插件如果只提供 `config.schema.json`，也允许安装，但前端高级类型体验会降级。
- 初版前端配置表单只支持 JSON Schema 生成，不支持插件提供自定义前端扩展。

不共享内容：

- Agent 推理逻辑。
- 交易策略实现。
- 数据源关键词。
- 私有行业知识。
- 交易 API 密钥和账户配置。

## Docker 与未来微服务化

从 0 到 1 阶段建议先保持单体部署，但按多入口设计：

```text
api container
worker container
scheduler container
web container
postgres container
```

早期可以共用同一 Python 镜像，通过不同 command 启动 API、worker、scheduler。后续如果需要微服务化，再把 worker、scheduler、source worker、agent runtime、broker gateway 拆成独立镜像。

## 初版落地建议

第一阶段只实现这些目录和能力：

- `apps/api`
- `apps/web`
- `apps/worker`
- `packages/core`
- `packages/agent`
- `packages/plugin-sdk`
- `packages/contracts`
- `plugins/sources`
- `plugins/industries`
- `runtime/plugins`

暂缓实现：

- 独立 `apps/scheduler` 的复杂调度能力。
- 多交易通道真实交易插件。
- 社区插件市场。
- 微服务拆分。

## 已暂缓问题

- 插件签名校验和来源白名单暂不进入初版。
- 外部 Secret Manager 暂不进入初版，后续在安全设计文档中单独讨论。
- 自定义前端插件扩展暂不进入初版，初版只支持 schema 生成配置表单。

## 待确认问题

1. 官方插件的发布版本是否跟随主仓库版本，还是每个插件独立版本？
2. 插件热重载的边界是什么：只重载配置，还是允许重载 Python 代码？
