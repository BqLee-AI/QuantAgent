# API v1 路由契约骨架规格

## ADDED Requirements

### Requirement: API v1 Router Structure

`apps/api` SHALL 暴露最小 API v1 资源结构，并区分 `routers/`、`schemas/`、`providers/` 职责。

#### Scenario: 路由分层可发现

- **WHEN** 开发者查看一个 API v1 资源实现
- **THEN** HTTP router 代码位于 `routers/`
- **AND** request/response DTO 位于 `schemas/`
- **AND** sample 或可替换的数据访问边界位于 `providers/`
- **AND** 开发者不需要为该资源重新发明文件落点约定

#### Scenario: API 层保持 HTTP 边界职责

- **WHEN** 开发者查看示例 provider
- **THEN** 其中不包含数据库访问、runtime 编排、插件 registry 访问、外部服务调用、credential 使用或核心领域逻辑
- **AND** 它清楚表达未来可被 core repository、runtime adapter、service 或 usecase 替换

### Requirement: Central API v1 Router Registration

API v1 routers SHALL 通过共享 helper 注册，而不是要求未来资源直接在 `main.py` 中手工接线。

#### Scenario: 存在标准 router 注册路径

- **WHEN** 开发者新增一个标准 API v1 router
- **THEN** 该 router 可以通过共享注册路径接入
- **AND** 该 router 挂载在已配置的 API v1 prefix 下
- **AND** 开发者可以明确标准 routers 在哪里被列出

#### Scenario: Router registration preserves app lifespan

- **WHEN** 应用通过 `create_app` 创建
- **THEN** 共享 router 注册 helper 不替换或绕过 FastAPI lifespan
- **AND** 已有数据库初始化和关闭逻辑仍在应用启动与关闭期间执行
- **AND** 标准 API v1 routes 通过同一个 app instance 暴露

#### Scenario: Debug router 在 production 中保持禁用

- **WHEN** 使用 production settings 创建 app
- **THEN** `/api/v1/debug/*` routes 不可访问
- **AND** production OpenAPI schema 中不存在 debug-only paths
- **AND** 标准 API v1 routes 仍然可访问

### Requirement: Non-business Example Resource

API SHALL 包含一个低风险、非业务含义的 API v1 示例资源。

#### Scenario: Version route 作为示例存在

- **WHEN** 客户端请求 `GET /api/v1/version`
- **THEN** 响应使用标准成功 envelope 并成功返回
- **AND** 该 route 带有用于 OpenAPI 发现的 tag
- **AND** route 名称和 payload 不暗示 runtime health、metadata aggregation、插件 registry、approval、Agent run、tool invocation、WebSocket、executor 或 live trading 能力

### Requirement: ApiResponse Envelope Convention

成功的 API v1 responses SHALL 使用 `ApiResponse[T]`，并通过显式 FastAPI response model 暴露该契约。

#### Scenario: Version route 使用 envelope

- **WHEN** 客户端请求 `GET /api/v1/version`
- **THEN** 响应体包含 `code`、`data`、`msg` 和 `error`
- **AND** `code` 为 `0`
- **AND** `error` 为 `null`
- **AND** `data` 只包含 `service`、`api_version`、`version`
- **AND** `service` 为非空字符串
- **AND** `api_version` 为非空字符串
- **AND** `version` 为非空字符串
- **AND** `data` 不包含任何额外字段

#### Scenario: 现有 health route 保持显式契约

- **WHEN** 客户端请求 `GET /api/v1/health`
- **THEN** 响应体保持为 `{"code": 0, "data": {"status": "ok"}, "msg": "ok", "error": null}`
- **AND** 该 route 暴露使用 `ApiResponse[T]` 的显式 `response_model`
- **AND** 该 route 带有 OpenAPI tag

#### Scenario: 现有 ready route 保持显式契约

- **WHEN** 客户端请求 `GET /api/v1/ready`
- **THEN** 数据库可用时响应体保持为 `{"code": 0, "data": {"status": "ready"}, "msg": "ok", "error": null}`
- **AND** 数据库未配置或不可用时继续返回统一 503 envelope
- **AND** 该 route 暴露使用 `ApiResponse[T]` 的显式成功 `response_model`
- **AND** 该 route 带有 OpenAPI tag

### Requirement: Schema And Provider Replacement Point

示例资源 SHALL 拆分 DTO schema 与 provider 替换点。

#### Scenario: DTO 位于 schemas 下

- **WHEN** 开发者查看示例资源的响应形状
- **THEN** response DTO 定义在 `schemas/` 下
- **AND** router 导入该 DTO，而不是返回临时的无类型 dictionary 契约

#### Scenario: Provider 仅作为 sample

- **WHEN** 开发者查看示例资源的数据来源
- **THEN** `providers/` 下的 provider 提供 sample data
- **AND** 该 provider 只表达未来替换边界
- **AND** 该 provider 不等同于已有请求级 DB session dependency
- **AND** 它不把自己表现为数据库 repository、Agent runtime、插件 registry、runtime health check、scheduler、Event Bus 或外部服务集成

### Requirement: OpenAPI Visibility And Contract Tests

仓库 SHALL 通过测试验证 API v1 route 可见性与 envelope 契约。

#### Scenario: Version route 在 OpenAPI 中可见

- **WHEN** 测试读取 development app 的 `/openapi.json`
- **THEN** schema 包含 `/api/v1/version`
- **AND** 该 path 带有显式 tags
- **AND** 成功响应引用或展开 `ApiResponse[...]` schema

#### Scenario: Health route 在 OpenAPI 中可见

- **WHEN** 测试读取 development app 的 `/openapi.json`
- **THEN** schema 包含 `/api/v1/health`
- **AND** 该 path 带有显式 tags
- **AND** 成功响应引用或展开 `ApiResponse[...]` schema

#### Scenario: Ready route 在 OpenAPI 中可见

- **WHEN** 测试读取 development app 的 `/openapi.json`
- **THEN** schema 包含 `/api/v1/ready`
- **AND** 该 path 带有显式 tags
- **AND** 成功响应引用或展开 `ApiResponse[...]` schema
- **AND** 该 route 的 OpenAPI 可见性不要求数据库在测试环境中已配置

#### Scenario: Production OpenAPI 排除 debug routes

- **WHEN** 测试读取 production app 的 `/openapi.json`
- **THEN** schema 不包含 `/api/v1/debug/error`
- **AND** schema 不包含 `/api/v1/debug/success`
- **AND** schema 仍包含标准 API v1 routes

### Requirement: No Static OpenAPI Artifact In This Change

本 change SHALL NOT 发布或更新静态 OpenAPI artifact。

#### Scenario: Runtime schema tests 作为契约检查

- **WHEN** 本 change 被实现
- **THEN** OpenAPI 验证基于 FastAPI runtime `/openapi.json`
- **AND** 不在 `packages/contracts/openapi/` 下新增文件
- **AND** 不在本 change 中生成 OpenAPI client、TypeScript types 或 Zod schema

### Requirement: Developer Documentation

`apps/api/README.md` SHALL 说明如何在本骨架下新增 API v1 router。

#### Scenario: README 记录 route 工作流

- **WHEN** 开发者阅读 `apps/api/README.md`
- **THEN** 开发者可以识别 router、schema 和 provider 文件应放在哪里
- **AND** 开发者可以识别 router 应如何注册
- **AND** 开发者可以识别预期的 `ApiResponse[T]`、`response_model`、tag 和测试约定
- **AND** README 说明本骨架不实现真实 event、plugin、approval、Agent、runtime、WebSocket、executor、live trading、generated client 或 static OpenAPI artifact 行为

#### Scenario: README 记录最小验证命令

- **WHEN** 开发者阅读 `apps/api/README.md`
- **THEN** README 包含 `cd apps/api && uv run python -m unittest discover -s src/tests`
- **AND** 该命令被描述为新增或调整 API v1 route 后的最小本地验证入口
