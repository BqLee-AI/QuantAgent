# 04. 技术架构

## 架构目标

技术架构需要支持事件实时接入、Agent 状态机编排、插件扩展、可解释推理、审批流和低延迟 UI 展示，同时保持 monorepo、Docker 部署和后续多容器演进空间。

## 总体架构

```text
Data Sources
  -> Source Plugins / RawEvent
  -> Event Bus
  -> Router Agent / AgentRuntime
  -> Industry Plugins / ToolRegistry / Skill Registry
  -> Scoring / Debate
  -> Decision / Policy Gate
  -> PostgreSQL / Audit
  -> Native WebSocket
  -> React Frontend
```

## 后端

### 技术选型

- 语言：Python 3.11+
- Web 框架：FastAPI
- Agent / Workflow：DeepAgents
- 数据库：PostgreSQL
- ORM：SQLAlchemy 2.x
- 迁移：Alembic

### 后端职责

- 接收来自 Source Plugin、外部 API 和调度任务的事件。
- 编排 Router Agent、行业包、Scoring / Debate 和 Decision / Policy Gate。
- 管理插件、审批、通知、运行状态和审计记录。
- 提供 REST API 和 Native WebSocket 实时通道。

## 运行时与仓库结构

初版 monorepo 以以下目录为主：

```text
apps/api
apps/web
apps/worker
apps/scheduler
packages/core
packages/agent
packages/plugin-sdk
packages/contracts
packages/prompts
plugins/
runtime/
infra/
```

### 职责边界

- `apps/api`：HTTP API、WebSocket、审批和管理接口。
- `apps/web`：React + Vite 管理台。
- `apps/worker`：事件处理、插件任务和异步作业。
- `apps/scheduler`：周期性调度。
- `packages/core`：核心领域、registry、错误、配置、数据库和生命周期。
- `packages/agent`：AgentRuntime 和 workflow。
- `packages/plugin-sdk`：插件开发 SDK。
- `packages/contracts`：OpenAPI、JSON Schema、生成代码。

## 插件与注册

- 所有插件通过 `plugin.yaml` 注册。
- Registry 扫描官方插件目录和 `runtime/plugins`。
- 插件配置通过 schema 驱动表单管理。
- ToolRegistry 和 Skill Registry 分别管理工具和 Skill 的授权与可见性。

## API 与实时通道

- HTTP API 使用资源 + `actions` 方式建模。
- 响应统一使用 `code/data/msg/error` envelope。
- 实时通道初版采用 Native WebSocket，负责增量通知，不作为业务状态真源。
- REST 是状态恢复基准，断线后必须重新拉取快照。

## 前端

### 技术选型

- 框架：React + Vite
- 路由：TanStack Router
- 服务端状态：TanStack Query
- UI 基础库：HeroUI v3

### 前端职责

- 展示事件流、运行时间线、插件状态和审批工作台。
- 通过生成的 API client 和 JSON Schema 消费后端契约。
- 只做 schema-driven 插件配置，不允许插件注入自定义前端组件。

## 部署与 Runtime

- 部署目标为 Docker。
- 初版保留 `api`、`worker`、`scheduler`、`web` 四类入口。
- `postgres` 和可选 `redis` 由 Docker Compose 管理。
- `runtime/` 保存插件、配置、数据、日志和隔离环境，不进入 Git。
- 初版 Event Bus 为进程内实现，后续可迁移到 Redis。
