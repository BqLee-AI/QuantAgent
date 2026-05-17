# Tasks: Initialize Project Tooling

## 1. Repository Skeleton

- [ ] 创建 `apps/api`、`apps/web`、`apps/worker`、`apps/scheduler`。
- [ ] 创建 `packages/core`、`packages/agent`、`packages/plugin-sdk`、`packages/adapters`、`packages/contracts`。
- [ ] 创建 `plugins/sources`、`plugins/industries`、`plugins/strategies`、`plugins/notifications`、`plugins/executors`。
- [ ] 创建 `runtime/plugins`、`runtime/config`、`runtime/data`、`runtime/logs`。
- [ ] 创建 `infra/docker` 和 `infra/compose`。

## 2. Backend Minimal App

- [ ] 添加 uv 使用的 Python project metadata。
- [ ] 在 `apps/api` 下添加 FastAPI application entrypoint。
- [ ] 添加 `GET /healthz`，返回 service name、status、version。
- [ ] 在 README 中添加最小 backend 启动命令。

## 3. Frontend Minimal App

- [ ] 添加 bun 使用的 Vite + React app metadata。
- [ ] 在 `apps/web` 下添加基础 app shell。
- [ ] 添加 health status panel，调用 backend health endpoint。
- [ ] 在 README 中添加最小 frontend 启动命令。

## 4. Database And Runtime Skeleton

- [ ] 在 core package 或团队约定的 infra migration 位置添加 Alembic skeleton。
- [ ] 为需要保留的 runtime 目录添加 `.gitkeep`。
- [ ] 更新 `.gitignore`，确保 runtime data、logs、local config、secrets、generated caches 不被提交。

## 5. Plugin Convention Seed

- [ ] 添加一个 placeholder source plugin directory。
- [ ] 添加最小 `plugin.yaml`，说明必需字段：`id`、`name`、`type`、`version`、`entrypoint`、`description`、`capabilities`、`config_schema`。
- [ ] 添加 placeholder config schema file。

## 6. Local Development

- [ ] 添加 Docker Compose skeleton，至少包含 `postgres`，并保留 app service placeholders。
- [ ] 文档中说明预期 local ports。
- [ ] 文档中说明 install 和 start commands。
- [ ] 验证 backend 和 frontend 可以独立启动。

## 7. Development Guidelines

- [ ] 统一项目开发规范，至少覆盖提交约定、代码格式化、检查命令、目录职责、敏感配置和生成产物边界。

## 8. Explicit Non-Goals

- [ ] 确认本 change 不实现 agent workflow、event routing、source crawling、real plugin loading、approval、notification、executor 或 trading behavior。
