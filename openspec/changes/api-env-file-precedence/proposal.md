## Why

`apps/api` 已经有独立 `.env` 入口，但当前文档把根目录 `.env` 表达为共享默认、API `.env` 只覆盖私有变量，无法支持 API 服务在本地、测试、staging、production 中独立覆盖 `APP_ENV`、`DATABASE_URL`、`RUNTIME_DIR`、`LOG_LEVEL` 等启动配置。随着 API 鉴权、数据库 readiness、外部 smoke gate 和 Docker 部署入口增多，需要把 API dotenv 优先级和多环境文件矩阵固化成可验证契约，避免根 `.env` 与 `apps/api/.env` 重复变量时行为不一致。

## What Changes

- 明确 API 运行时 dotenv 加载优先级：真实进程环境变量仍最高；在文件层面，`apps/api` 下的环境文件优先于仓库根目录 `.env`，允许重复变量，并以后加载的 API 文件覆盖根 `.env`。
- 引入 API 多环境 dotenv 命名约定，例如 `apps/api/.env.local`、`apps/api/.env.test`、`apps/api/.env.staging`、`apps/api/.env.production`，并保留不提交真实 secret 的安全边界。
- 明确 Docker Compose 路径的特殊风险：Compose 当前会把根 `.env` 展开为容器环境变量，环境变量优先级高于应用内 dotenv；实现必须调整该边界，确保 API 应用配置不会被根 `.env` 通过 `environment:` 反向提升为最终真源。
- 更新 API README、API `.env.example`、必要的根 `.env.example` / `docker-compose.yml` 说明，使开发者能按环境选择正确文件。
- 增加最小测试覆盖，证明重复变量时 API 文件优先、环境特定文件按顺序覆盖、真实环境变量仍最高。
- 不改变 API 路由、鉴权语义、数据库 schema、Alembic migration、前端运行时配置或插件配置真源。

## Capabilities

### New Capabilities

- `api-env-file-precedence`: API dotenv 文件优先级、多环境文件选择和 Compose/文档一致性契约。

### Modified Capabilities

- 无。

## Impact

- 代码：`apps/api/src/quantagent/api/config/settings.py`、必要的 API 配置测试。
- 文档与示例：`apps/api/README.md`、`apps/api/.env.example`、API 多环境 `.example` 模板、根目录 `.env.example`。
- 部署入口：根目录 `docker-compose.yml` 需要收敛 `api.environment` 的硬注入范围，避免把 API 应用配置从根 `.env` 提升为真实进程环境变量。
- Git 忽略规则：根 `.gitignore` 需要继续忽略真实 `.env*`，并放行协作所需的 `.env.*.example` 模板。
- 依赖：不新增运行时依赖；继续基于已安装的 `pydantic-settings` dotenv 行为。
- 安全：不得提交真实 secret、生产数据库地址或个人本地配置；production/staging 文件只能作为非敏感模板，真实 secret 继续通过环境变量、CI secret 或未来 Secret Manager 注入。
