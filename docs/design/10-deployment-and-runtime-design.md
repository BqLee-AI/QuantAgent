# 10. 部署与 Runtime 设计

## 文档状态

**状态**：正式草案 v0.2  
**范围**：Docker Compose、服务拆分、镜像策略、环境变量、runtime 目录、插件持久化、开发/生产启动方式、migration、日志、健康检查、消息总线演进  
**当前约定**：部署目标为 Docker；初版保留 API、worker、scheduler、web 多入口；数据库使用 PostgreSQL；Event Bus 默认使用内存 fake，并通过 optional Kafka profile 提供跨进程运行时  
**不包含**：Kubernetes、云厂商 Secret Manager、生产级监控告警平台、插件签名系统、真实交易所网络隔离

## 设计前提

- 项目从 0 到 1 阶段保持单体可运行，但目录和容器边界要支持未来多容器、微服务和 Kafka Event Bus 扩展。
- API、worker、scheduler 是不同运行入口，但可以共用同一个 Python 镜像。
- Web 是 React + Vite 构建产物，生产环境不应该依赖 Vite dev server。
- PostgreSQL 是初版必选服务。
- `runtime/` 保存运行时数据、私有插件、配置、日志和本地 secret，不应进入 Git。
- 官方插件在 `plugins/`，可以随代码进入镜像；第三方、社区、私有插件放在 `runtime/plugins/`，通过 volume 挂载。
- 插件依赖可以自动安装，但必须受控、可审计、可回滚或可重建。

## 设计原则

- 部署目标以 Docker 为主，本地开发可以使用 uv / bun 原生命令。
- API、worker、scheduler 是不同运行入口，但可共用同一个 Python runtime 镜像。
- Web 生产部署使用静态服务，不跑 Vite dev server。
- `runtime/` 保存插件、配置、数据、日志和隔离依赖环境，不进入 Git。
- 运行时依赖必须可重建、可审计、可隔离。
- 普通本地开发默认使用内存 fake；需要跨进程分发时显式启用 Kafka profile。

## Docker Compose 结构

初版 Compose 包含以下服务：

```text
postgres
migrate
api
worker
scheduler
web
kafka      # optional profile
```

启动依赖：

```text
postgres
  -> migrate
  -> api / worker / scheduler
  -> web
```

规则：

- `api`、`worker`、`scheduler` 共用 Python runtime 镜像，用不同 command 启动。
- `web` 使用独立前端构建镜像和静态服务。
- `postgres` 使用持久化 volume。
- `kafka` 作为 optional profile，不默认启用。
- `migrate` 执行 Alembic upgrade 后退出。

## 镜像策略

### Python runtime 镜像

`api`、`worker`、`scheduler` 共用一个 Python runtime 镜像。

好处：

- 构建简单。
- 依赖一致。
- 代码共享自然。
- 适合 monorepo 和初版部署。

运行示例：

```text
api       -> uv run quantagent-api
worker    -> uv run quantagent-worker
scheduler -> uv run quantagent-scheduler
```

### Web 镜像

Web 使用独立构建镜像，先 `bun run build`，再由静态服务对外提供资源。

规则：

- 生产环境不跑 Vite dev server。
- 可以由 Nginx、Caddy 或轻量 Node 静态服务托管。
- WebSocket 反向代理由静态服务层或外层代理统一处理。

## runtime 目录

运行时目录按职责分开挂载：

```text
./runtime/plugins:/app/runtime/plugins
./runtime/config:/app/runtime/config
./runtime/data:/app/runtime/data
./runtime/logs:/app/runtime/logs
./runtime/plugin-envs:/app/runtime/plugin-envs
```

目录职责：

| 目录 | 职责 | 是否进 Git |
| --- | --- | --- |
| `runtime/plugins` | 第三方、社区、私有插件 | 否 |
| `runtime/config` | 本地配置、secret reference、策略配置 | 否 |
| `runtime/data` | 本地缓存、临时数据、导入导出 | 否 |
| `runtime/logs` | 文件日志、插件安装日志 | 否 |
| `runtime/plugin-envs` | 插件隔离依赖环境 | 否 |

规则：

- 官方插件可以随代码进入镜像。
- 第三方、社区、私有插件放在 `runtime/plugins`。
- `runtime/config` 只保存本地配置、override 和 secret reference，不保存真实密钥。
- `runtime/plugin-envs` 保存插件隔离依赖，不污染主 Python 环境。

## 配置与 secret 分层

配置分层如下：

```text
.env
  -> 基础启动配置，例如 database url、runtime path、mode

runtime/config/app.yaml
  -> 应用运行配置，例如 feature flags、默认策略

runtime/config/plugins/
  -> 插件本地配置模板或 override

数据库 plugin_configs
  -> 插件当前运行时配置真源

secret reference
  -> 环境变量、本地 secret 文件或未来 Secret Manager
```

规则：

- `.env` 可以提供默认启动配置，但不得提交真实密钥。
- `runtime/config/secrets.*` 默认不进 Git。
- API 响应不得返回 secret 原文。
- 插件配置变更以数据库为运行时真源。
- 文件配置主要用于 bootstrap、默认值、本地部署和 secret reference。

## Migration

Alembic migration 由独立 `migrate` service 执行。

流程：

```text
migrate -> alembic upgrade head
api depends_on migrate success
```

规则：

- 生产环境避免多个 API 实例同时自动迁移。
- `migrate` 失败时 Compose 不应继续拉起 API。
- 本地允许手动命令辅助迁移。

## 开发与生产模式

开发环境使用 uv / bun 原生命令，基础依赖用 Docker。

示例：

```text
docker compose up postgres
uv run quantagent-api
uv run quantagent-worker
uv run quantagent-scheduler
bun run dev
```

规则：

- 开发环境优先速度。
- 生产环境优先一致性和可重建。
- 插件开发和热重载优先在开发环境完成。

## 日志

应用结构化日志输出 stdout，重要运行时和插件日志写入 `runtime/logs`。

规则：

- stdout 用于容器日志和平台日志收集。
- `runtime/logs` 用于本地排查、插件安装日志、运行时审计补充。
- 日志不得输出 secret、完整 prompt、私有策略明文。
- 后续可以接 OpenTelemetry / Loki / ELK。

## 健康检查

每个服务提供健康状态，API 聚合 runtime health。

初版 health 维度：

- API 是否可用。
- PostgreSQL 是否可连接。
- migration version。
- worker heartbeat。
- scheduler heartbeat。
- plugin registry 状态。
- runtime path 是否可写。
- web build/version。

规则：

- 健康检查应区分 liveness 与 readiness。
- 前端 runtime 页面可直接读取聚合健康状态。
- 服务健康变化必须能进入审计或运行记录。

## Kafka Event Bus 运行时

普通本地开发和单元测试默认使用内存 fake。需要跨进程分发时，Compose 提供 `kafka` optional profile。

规则：

- 初版不强制启用 Kafka。
- Compose 可以提供 `kafka` service，但放在 optional profile。
- `api` 不承担长期 consumer loop；`worker` / `scheduler` 作为 Event Bus composition root。
- EventEnvelope、topic、correlation_id、causation_id、schema_version 在内存 fake 和 Kafka backend 间保持一致。
- RawEvent / Event 持久化、outbox、replay、DLQ 数据库记录不在当前 phase。

## 插件依赖自动安装

插件 Python 依赖安装到 `runtime/plugin-envs` 的隔离环境。

规则：

- 不污染主 Python 环境。
- 支持按插件 ID 和版本重建。
- 安装和失败必须记录日志和审计。
- 插件独立容器作为后续增强，不进入初版。

## 当前推荐结论汇总

- Docker Compose 初版包含 `postgres`、`migrate`、`api`、`worker`、`scheduler`、`web`，Kafka 作为 optional profile。
- API、worker、scheduler 共用 Python runtime 镜像，用不同 command 启动。
- Web 独立构建并使用静态服务，不在生产跑 Vite dev server。
- runtime 目录按 plugins、config、data、logs、plugin-envs 分开挂载。
- 配置分层为 `.env` / `runtime/config` / DB plugin_configs / secret reference。
- Migration 使用独立 `migrate` service 执行 Alembic。
- 开发环境使用 uv/bun 原生命令，Docker 只跑基础依赖。
- 日志同时输出 stdout 和 `runtime/logs`，敏感内容必须脱敏。
- 每个服务需要健康检查，API 聚合 runtime health。
- 插件 Python 依赖安装到 `runtime/plugin-envs` 隔离环境。
