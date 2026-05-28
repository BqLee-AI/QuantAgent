## Context

当前 API 配置由 `apps/api/src/quantagent/api/config/settings.py` 中的 `Settings` 继承 `quantagent.core.config.settings.Settings`，通过 `pydantic-settings` 读取 dotenv 文件。现有 `_build_env_files()` 已包含仓库根目录 `.env` 和 `apps/api/.env`，并且 `pydantic-settings` 对多个 dotenv 文件按列表顺序读取、后读覆盖先读，因此直跑 API 时已经具备“API `.env` 覆盖根 `.env`”的基础。

当前缺口在于契约不完整：

- `apps/api/README.md` 和 `apps/api/.env.example` 仍把根 `.env` 描述为共享变量入口，把 API `.env` 限定为 API 私有变量覆盖。
- 没有为 `local`、`test`、`staging`、`production` 定义 API 多环境 dotenv 文件矩阵。
- `docker-compose.yml` 通过 `environment:` 把根 `.env` 展开成容器环境变量，而环境变量优先级高于应用内 dotenv；如果不处理，Compose 路径会绕过“API 文件优先”的设计。
- 根 `.gitignore` 忽略 `.env.*`，这符合 secret 安全边界，但需要明确真实 `.env.*` 不提交，若需要提交模板必须使用并放行 `.example` 文件。

本 change 只定义 API 启动配置契约，不改变业务路由、鉴权策略、数据库模型、插件配置真源或前端运行时配置。

## Goals / Non-Goals

**Goals:**

- 让 `apps/api/.env` 及 `apps/api/.env.<env>` 在文件层面优先于仓库根 `.env`，并允许重复变量。
- 支持一套可解释、可测试的 API 环境文件矩阵，覆盖本地开发、测试、staging 和 production。
- 保持真实进程环境变量 / CI secret / Secret Manager 注入的最高优先级，避免 dotenv 文件覆盖受控 secret。
- 让直跑 API、从仓库根目录运行、从 `apps/api` 目录运行和 Docker Compose 路径的配置行为可预测。
- 更新 README、示例文件和测试，确保后续开发者不再依赖过期语义。

**Non-Goals:**

- 不引入新配置库、Secret Manager SDK 或运行时配置服务。
- 不把真实 secret、生产数据库地址、个人本地配置或私有策略写入仓库。
- 不改变 `packages/core` 的通用 `Settings` 对非 API 调用方的默认 `.env` 行为，除非实现时证明必须补充共享 helper。
- 不调整 API 鉴权规则、session 语义、route 注册、数据库 migration 或前端 `import.meta.env` 契约。
- 不要求 Docker 镜像内烘焙真实 dotenv 文件；容器路径的 secret 继续通过外部环境、CI/CD secret、挂载文件或未来 Secret Manager 注入。

## Source of Truth and Paths

- Canonical contract: 本 change 的 `specs/api-env-file-precedence/spec.md` 定义 API dotenv 优先级、环境选择、模板安全和 Compose 边界的验收要求。
- Canonical implementation path: `apps/api/src/quantagent/api/config/settings.py` 中的 API `Settings` 和 dotenv helper。API 私有加载规则不应下沉为 `packages/core` 对所有调用方生效的默认行为。
- Canonical documentation path: `apps/api/README.md`、`apps/api/.env.example`、API 多环境 `.example` 模板、根 `.env.example` 和 `docker-compose.yml` 注释/结构共同解释运行入口。
- Fallback path: 如果实现过程中发现 `pydantic-settings` 的 `SettingsConfigDict(env_file=...)` 无法表达两阶段候选列表，可以在 API 配置模块内新增小型 helper 并通过 `_env_file` 或等价入口在测试中隔离验证。
- Forbidden bypass: 不允许通过在 `docker-compose.yml` 的 `api.environment` 中继续硬注入 `APP_ENV`、`DATABASE_URL`、`RUNTIME_DIR`、`LOG_LEVEL`、`AUTH_*`、`API_*` 来规避 API dotenv 优先级；不允许提交真实 `.env`、`.env.*`、生产数据库地址或 secret。

## Decisions

### 1. 文件优先级采用“根默认，API 覆盖，环境特定再覆盖”

API dotenv 文件加载顺序设计为从低到高：

```text
.env
apps/api/.env
apps/api/.env.local
apps/api/.env.<APP_ENV>
apps/api/.env.<APP_ENV>.local
```

真实进程环境变量仍高于所有 dotenv 文件，代码默认值低于所有 dotenv 文件。

理由：

- 根 `.env` 继续承担 monorepo 和 Compose 默认值入口，兼容现有本地流程。
- `apps/api/.env` 成为 API 默认覆盖层，可重复定义 `APP_ENV`、`DATABASE_URL`、`RUNTIME_DIR`、`LOG_LEVEL`、`AUTH_*`、`API_*`。
- `.env.local` 适合开发者本机私有覆盖；`.env.<APP_ENV>` 适合环境级默认；`.env.<APP_ENV>.local` 适合某个环境的私有覆盖。
- `pydantic-settings` 已支持多个 dotenv 后读覆盖先读，不需要新增依赖。

替代方案：只保留 `.env` 与 `apps/api/.env` 两层。该方案简单，但无法表达测试和生产差异，会继续鼓励开发者在一个文件里混放环境变量。

### 2. `APP_ENV` 的发现分两阶段处理

实现应先从真实环境变量读取 `APP_ENV`，如果没有，再从基础 dotenv 层解析出 `APP_ENV`，用于决定是否追加 `apps/api/.env.<APP_ENV>` 和 `apps/api/.env.<APP_ENV>.local`。基础层包含根 `.env`、`apps/api/.env` 和固定候选 `apps/api/.env.local`；如果这些文件同时定义 `APP_ENV`，按基础层文件加载顺序后者覆盖前者。随后再构造完整 dotenv 列表交给 `SettingsConfigDict(env_file=...)` 或等价的 API settings 初始化入口。

理由：

- 如果 `APP_ENV=production` 由 CI/CD 或容器环境注入，应优先决定 production 文件候选。
- 如果开发者只在 `apps/api/.env` 或 `apps/api/.env.local` 写 `APP_ENV=test`，也应能自动加载 `apps/api/.env.test`。
- 不要求加载全部 `.env.*` 文件，避免 `.env.production` 被 development 误读。

替代方案：总是加载所有已知 `.env.local/.env.test/.env.production`。该方案容易让 production/test 配置串扰，不采用。

### 3. 真实 dotenv 文件默认不提交，提交 `.example` 模板

运行时支持读取真实文件：

```text
apps/api/.env
apps/api/.env.local
apps/api/.env.test
apps/api/.env.staging
apps/api/.env.production
apps/api/.env.<APP_ENV>.local
```

源码中只提交非敏感模板：

```text
apps/api/.env.example
apps/api/.env.local.example
apps/api/.env.test.example
apps/api/.env.staging.example
apps/api/.env.production.example
```

如果采用 `.env.*.example` 模板，需要同步调整 `.gitignore`，显式放行 `!.env.*.example`；真实 `.env.*` 继续忽略。

理由：

- 满足多环境文件设计，同时遵守“不提交真实 secret、生产数据库地址或本地个人配置”的仓库规则。
- 模板文件可以给出变量清单和默认值，但 production/staging 模板中的 secret 字段只能留空或写 `change-me` 占位。

替代方案：提交真实 `.env.test`。该方案对测试默认值很方便，但会和全局 `.env.*` 忽略规则、安全规则冲突；如后续确实需要，可单独讨论是否只放行 `apps/api/.env.test`。

### 4. Compose 不应把 API 应用变量从根 `.env` 硬注入为最终真源

Compose 路径需要避免根 `.env` 通过 `environment:` 覆盖 API dotenv。本 change 决定采用保守的方案 B：Compose 插值只用于 Compose 自身端口、镜像、数据库服务和容器必须强制的启动参数，不把 API 应用配置从根 `.env` 硬注入为最终进程环境变量。

具体约束：

- Compose 可以通过 `command` 或等价启动参数固定容器网络入口，避免把 `HOST`、`PORT` 注入为 API Settings 可见的真实环境变量。
- `api.environment` 不应继续硬注入 `APP_ENV`、`DATABASE_URL`、`RUNTIME_DIR`、`LOG_LEVEL`、`AUTH_*`、`API_*` 等 API 应用配置。
- 容器侧 `DATABASE_URL` 仍必须有清晰入口，推荐通过 `apps/api/.env` 或 `apps/api/.env.<APP_ENV>` 的容器专用值提供，例如指向 `db:5432`；宿主机直跑继续可在根 `.env` 或 API dotenv 中使用 `localhost:15432`。
- 如果某个部署环境必须用真实进程环境变量覆盖 dotenv，应在 README 和 PR 说明中明确它是有意的最高优先级覆盖，而不是 Compose 根 `.env` 的隐式反向覆盖。

### 5. 测试聚焦配置解析，不启动真实服务

新增或更新 API 配置测试时，应使用临时目录构造根 `.env` 和 `apps/api/.env*`，避免读取开发者本机真实 `.env`。测试可以直接覆盖 `_env_file` 或新增小型 helper 来构造候选列表；如果修改 `_build_env_files()`，需要测试：

- 重复变量时 `apps/api/.env` 覆盖根 `.env`。
- `APP_ENV=test` 时 `.env.test` 覆盖基础 API `.env`，且 `.env.production` 等未选中文件不参与加载。
- 真实环境变量覆盖所有 dotenv 文件。
- production/staging 缺失必要 secret 时仍触发现有 `Settings` 校验。
- Compose 调整至少用 `docker compose config` 验证配置可解析，并人工检查 `api.environment` 不再把根 `.env` 的 API 应用变量提升为进程环境变量。

## Deferred / Out of Phase

- Secret Manager SDK、加密 secret 文件、CI/CD secret 注入模板和生产部署平台配置不进入本 change。
- worker、scheduler、web 的 dotenv 多环境矩阵不进入本 change；如后续需要，应单独开 change，避免把 API 私有加载规则误推广为全仓规则。
- Docker 镜像内是否复制 `.env.example` 或真实 dotenv 文件不在本 change 中保证；本 change 只要求 Compose 路径不反转 API dotenv 优先级。

## Risks / Trade-offs

- [Risk] `APP_ENV` 两阶段发现逻辑如果读取顺序实现错误，可能加载错误的环境文件。→ Mitigation：把候选列表构造拆成可测试 helper，并用临时文件覆盖 `APP_ENV` 来验证顺序。
- [Risk] Compose 中 `DATABASE_URL` 对宿主机和容器不同，简单移除 `environment:` 可能导致容器连接 localhost。→ Mitigation：Compose 调整必须保留容器侧数据库 URL 来源，并用 `docker compose config` 验证最终配置。
- [Risk] `.env.production` 被误提交或包含 secret。→ Mitigation：真实 `.env*` 继续忽略，只提交 `.example` 模板；README 明确 production secret 通过环境变量或 Secret Manager 注入。
- [Risk] 修改 API 配置 helper 影响测试 import 时的全局 `settings = Settings()`。→ Mitigation：测试使用 `_env_file=None` 或临时 `_env_file`，避免依赖开发者本机 `.env`；实现后运行 API unittest。
- [Risk] 根 `.env` 和 API `.env` 同时定义 `APP_ENV` 可能让开发者困惑。→ Mitigation：README 写清文件层面 API 优先，真实环境变量最高；建议根 `.env` 用于 monorepo 默认，API `.env` 用于 API 进程最终默认。
