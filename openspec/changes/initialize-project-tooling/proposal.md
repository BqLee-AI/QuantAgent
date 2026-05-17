# Change: Initialize Project Tooling

## Why

QuantAgent 已经有 PRD 和架构设计，但仓库还需要一个很小、可运行、可继续扩展的起步点。这个起步点应该先于 Agent、插件、事件路由和交易逻辑。

本 change 已经用 OpenSpec 生成项目初始阶段的任务、需求和验收场景，定义项目最初 1-2 天的阶段工具初始化范围。目标是让项目先具备可启动、可维护、边界清楚的开发工具和工程骨架，同时避免一开始就把完整业务复杂度塞进地基里。

## What Changes

- 创建初始 monorepo 目录，包括 backend、frontend、shared packages、plugins、runtime 和 infra。
- 添加最小 FastAPI app，并提供 health endpoint。
- 添加最小 React + Vite app，可以渲染基础页面并调用后端 health endpoint。
- 添加 Python 和前端 package manager metadata。
- 添加本地开发用 Docker Compose 骨架。
- 添加 Alembic migration 骨架，但暂不定义产品业务表。
- 添加 `runtime/` 目录约定，并通过 `.gitignore` 排除本地运行状态。
- 添加一个占位插件 manifest，固定 `plugin.yaml` 的基础约定。
- 在 README 中补充启动命令、目录说明和初始开发约定。
- 在任务中提示后续需要完成开发规范统一。

## Out Of Scope

- 事件接入和 Event Bus 实现。
- Router Agent、AgentRuntime、DeepAgents 集成和 provider 管理。
- 真实 source plugins、industry packages、ToolRegistry、Skill Registry、scoring、approval、notification 或 executor 逻辑。
- events、plugins、decisions、approvals、audits 等真实业务表结构。
- 认证、权限和生产级 secrets 管理。
- 生产 Docker 镜像优化。

## Success Criteria

- 开发者可以 clone 仓库、安装依赖，并在本地启动 backend 和 frontend。
- Backend 暴露 health endpoint。
- Frontend 渲染基础 app shell，并能展示 backend health status。
- 仓库包含后续开发约定好的目录边界。
- Migration 工具有明确位置，即使本 change 不实现业务表。
- 占位 `plugin.yaml` 能说明未来插件应遵循的基本形态。
- README 和 OpenSpec 能让开发者快速理解项目起步状态。
- 初始任务清单包含开发规范统一事项，避免后续工程实现缺少共同约定。
