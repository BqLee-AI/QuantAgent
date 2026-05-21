## ADDED Requirements

### Requirement: API 源码目录分层

`apps/api` SHALL 使用显式源码目录表达 FastAPI HTTP 边界、API 私有鉴权边界和 API v1 route 注册边界。

#### Scenario: HTTP 传输层基础能力集中在 http 边界

- **WHEN** 实现迁移响应信封、API 层错误类型、异常处理注册和 Request ID middleware
- **THEN** 这些能力被归入明确的 HTTP 传输层目录
- **AND** 该目录不承载数据库访问、业务流程、插件 Registry、Agent workflow、交易策略判断或可复用领域逻辑

#### Scenario: API 私有鉴权拆分在 auth 边界

- **WHEN** 实现迁移当前本地 Cookie Session 鉴权代码
- **THEN** actor/capability、session/cookie、CSRF/dependency 和 audit context 职责被拆入明确的 auth 模块边界
- **AND** session refresh 逻辑仍属于 session/cookie 边界，并且只基于当前 `CurrentActor` 的 actor id 和 capability snapshot 重签 session
- **AND** 该模块仍属于 `apps/api` 私有能力
- **AND** 实现不得在没有新增复用方和 OpenSpec 依据的情况下把该鉴权能力上移到 `packages/core`

#### Scenario: API v1 routes 使用显式版本边界

- **WHEN** 实现迁移标准 API v1 route 和 route registration helper
- **THEN** route 文件和 `STANDARD_API_V1_ROUTER_REGISTRATIONS` 被收敛到显式 v1 路由边界
- **AND** 标准 API v1 routes 仍通过统一 registration helper 注册
- **AND** 实现不得在 `main.py` 零散新增标准 API v1 `include_router(...)`

#### Scenario: 不创建业务核心层占位目录

- **WHEN** 实现创建新的 API 源码目录
- **THEN** 新目录必须承接当前已有代码职责
- **AND** 实现不得创建空的 `services`、`repositories`、`domain`、`models`、`usecases` 或同类未来占位目录
- **AND** 实现不得借目录重构把核心领域逻辑放入 `apps/api`

### Requirement: 目录重构保持 API 外部行为不变

`apps/api` 目录重构 MUST NOT 改变现有 API runtime 行为、OpenAPI 契约、鉴权语义或 readiness 语义。

#### Scenario: 现有 API 路径和响应契约保持不变

- **WHEN** 目录重构完成后客户端调用现有 API v1 routes
- **THEN** `/api/v1/health`、`/api/v1/ready`、`/api/v1/version`、`/api/v1/auth/login`、`/api/v1/auth/logout` 和 `/api/v1/me` 的路径保持不变
- **AND** 成功和失败响应继续使用 `code/data/msg/error` envelope
- **AND** OpenAPI 中现有 paths、tags、response_model 和 envelope schema 不因目录重构发生行为性变化

#### Scenario: public 和 protected route policy 保持不变

- **WHEN** 目录重构完成后 API v1 route registration 运行
- **THEN** public allowlist 仍只包含 `GET /api/v1/health`、`GET /api/v1/ready`、`GET /api/v1/version` 和 `POST /api/v1/auth/login`
- **AND** 未列入 public allowlist 的 API v1 route 仍默认 protected
- **AND** 非 production debug routes 不会加入 public allowlist
- **AND** production 环境仍不注册或暴露 debug-only paths

#### Scenario: Cookie Session 和 CSRF 行为保持不变

- **WHEN** 目录重构完成后执行登录、登出、当前用户和受保护写操作
- **THEN** login 仍只通过 HttpOnly cookie 建立 session 并返回非敏感 `csrf_token`
- **AND** logout 仍要求有效 session 和有效 CSRF token
- **AND** `/api/v1/me` 在 session 模式下仍刷新 HttpOnly session cookie，并返回随新 session 派生的非敏感 `csrf_token`
- **AND** `/api/v1/me` 仍返回 actor、capabilities 和非敏感 `csrf_token`
- **AND** development auth bypass 下 `/api/v1/me` 仍返回 development actor 和稳定 CSRF token，且不签发 session cookie
- **AND** 响应体不得返回 raw session、cookie value、signing secret、password、password hash、secret 或 traceback

#### Scenario: readiness 和 health 语义保持不变

- **WHEN** 目录重构完成后调用 health 和 readiness probe
- **THEN** `GET /api/v1/health` 仍只验证 API 进程存活
- **AND** `GET /api/v1/ready` 仍只验证已配置数据库可达
- **AND** readiness probe 可以复用请求级 DB session dependency 执行轻量连接验证
- **AND** readiness probe 不得依赖 sample provider 或业务表结构

### Requirement: 最小兼容 import 和文档同步

`apps/api` 目录重构 SHALL 使用最小兼容 import 策略，并同步长期开发说明。

#### Scenario: 内部引用迁移到新路径

- **WHEN** 实现迁移源码和测试 import
- **THEN** 内部引用优先使用新的 `http`、`auth` 和 `routers/v1` 路径
- **AND** 新增代码示例和文档不得继续引导使用旧路径

#### Scenario: 高风险旧入口可保留薄 re-export

- **WHEN** 旧 import 路径被测试、文档、仓库内其他 app/package 或可能的外部脚本直接引用
- **THEN** 实现可以为该高风险公共入口保留薄 re-export
- **AND** re-export 不得包含新的业务逻辑
- **AND** re-export 不得扩大为所有旧路径的长期全量兼容层

#### Scenario: 纯内部旧路径不保留兼容入口

- **WHEN** 旧 import 路径只被 `apps/api` 内部实现互相引用
- **THEN** 实现必须把该引用迁移到新路径
- **AND** 实现不得只为减少迁移改动而保留旧路径 re-export

#### Scenario: README 和 AGENTS 与实际结构一致

- **WHEN** 目录重构完成
- **THEN** `apps/api/README.md` 的目录说明、新增 route 流程、auth 边界和最小验证说明与实际代码一致
- **AND** `apps/api/AGENTS.md` 的关键目录索引和本地规则与实际代码一致
- **AND** 文档明确 `apps/api` 只承载 HTTP/API 传输层，不承载可复用核心领域逻辑
