# Project Tooling Specification

## ADDED Requirements

### Requirement: Monorepo Foundation

项目 SHALL 提供最小 monorepo 目录结构，用于承载 backend apps、frontend apps、shared packages、plugins、runtime state 和 infra assets。

#### Scenario: Required directories exist

- **WHEN** 开发者在 initialize-project-tooling change 完成后检查仓库
- **THEN** `apps/api`、`apps/web`、`apps/worker`、`apps/scheduler` 存在
- **AND** `packages/core`、`packages/agent`、`packages/plugin-sdk`、`packages/adapters`、`packages/contracts` 存在
- **AND** `plugins/sources`、`plugins/industries`、`plugins/strategies`、`plugins/notifications`、`plugins/executors` 存在
- **AND** `runtime/plugins`、`runtime/config`、`runtime/data`、`runtime/logs` 存在
- **AND** `infra/docker` 和 `infra/compose` 存在

### Requirement: Minimal Backend Entrypoint

项目 SHALL 包含一个最小 FastAPI backend entrypoint，并且它可以在没有产品数据、没有真实插件实现的情况下启动。

#### Scenario: Backend health endpoint responds

- **WHEN** backend 在本地运行
- **AND** 开发者请求 `GET /healthz`
- **THEN** 响应表明服务健康
- **AND** 响应至少包含 service name、status、version

### Requirement: Minimal Frontend Entrypoint

项目 SHALL 包含一个最小 React + Vite frontend app，可以独立启动，并展示 backend health status。

#### Scenario: Frontend renders app shell

- **WHEN** frontend dev server 正在运行
- **THEN** 浏览器展示基础 QuantAgent app shell
- **AND** app 会从配置的 backend URL 读取 backend health status

### Requirement: Package Manager Baseline

项目 SHALL 为 backend 和 frontend development 定义 package manager metadata。

#### Scenario: Developer sees install commands

- **WHEN** 开发者阅读 README
- **THEN** README 说明 backend dependency setup 所需的 uv command
- **AND** README 说明 frontend dependency setup 所需的 bun command

### Requirement: Database Migration Skeleton

项目 SHALL 包含 Alembic migration skeleton，但 initialize-project-tooling change 不要求定义任何产品业务表。

#### Scenario: Migration location is defined

- **WHEN** 开发者检查仓库
- **THEN** 仓库中有明确 migration directory
- **AND** initialize-project-tooling change 暂不定义 event、plugin、decision、approval 或 audit tables

### Requirement: Runtime State Boundary

项目 SHALL 区分可提交的 source code 和本地 runtime state。

#### Scenario: Runtime state is ignored

- **WHEN** 本地 runtime config、logs、plugin installs、data files 或 secrets 被创建在 `runtime/` 下
- **THEN** git 不应把这些本地 runtime files 当作普通 source files 提交
- **AND** 只允许通过 placeholder files 保留必要目录

### Requirement: Plugin Manifest Convention Seed

项目 SHALL 包含一个 placeholder plugin manifest，用于建立未来插件约定。

#### Scenario: Placeholder plugin manifest exists

- **WHEN** 开发者打开 placeholder plugin
- **THEN** 其中包含 `plugin.yaml`
- **AND** manifest 包含 `id`、`name`、`type`、`version`、`entrypoint`、`description`、`capabilities`、`config_schema`
- **AND** 该 plugin 不实现真实 crawling 或 business logic

### Requirement: Local Development Compose Skeleton

项目 SHALL 包含用于 local development 的 Docker Compose skeleton。

#### Scenario: Compose file documents local services

- **WHEN** 开发者打开 compose file 或 README
- **THEN** PostgreSQL 被列为 local dependency
- **AND** app service placeholders 或 comments 说明 API、worker、scheduler、web 后续如何加入

### Requirement: Development Guidelines Baseline

项目 SHALL 在初始阶段明确需要统一开发规范，避免后续工程搭建和业务实现缺少共同约定。

#### Scenario: Development guideline task exists

- **WHEN** 开发者阅读初始阶段 tasks
- **THEN** 可以看到统一项目开发规范的任务
- **AND** 该任务覆盖提交约定、代码格式化、检查命令、目录职责、敏感配置和生成产物边界

### Requirement: Tooling Scope Guard

initialize-project-tooling change SHALL NOT 实现超出阶段工具初始化之外的产品行为。

#### Scenario: No product workflow is implemented

- **WHEN** initialize-project-tooling change 被评审
- **THEN** 它不实现真实 event ingestion、event routing、agent workflows、source crawling、plugin loading、approval、notification、executor 或 trading behavior
- **AND** 未来产品行为仍保留在 PRD 和 design documents 中，不隐藏在 tooling 初始化代码里
