## Why

`add-api-structured-file-logging` 已经建立 API 结构化文件日志闭环，但当前按小时切分会在长期运行时产生过多小文件；同时 `RUNTIME_DIR=runtime` 的默认相对路径会随启动 cwd 漂移，导致本地日志和运行时数据分散。现在需要在不破坏 stream 语义、脱敏、队列写入和 disk guard 的前提下，降低文件数量并稳定默认运行时落点。

## What Changes

- 保留 `access`、`app`、`error`、`security`、`audit` 五个逻辑 stream，不合并物理 stream，不改变结构化字段和事件语义。
- 将 API 文件日志从“按小时 + 大小轮转”改为“按天 + 大小轮转”：文件名时间片从 `YYYYMMDDTHH` 改为 `YYYYMMDD`，同一 `{service, env, instance_id, pid, stream, date}` 活跃 writer 内只因大小阈值产生 `.part-NNN`。
- 将 `access` stream 默认 retention 从 7 天下调为 3 天；`app=14`、`error=30`、`security=30`、`audit=90` 保持不变。
- 稳定默认 runtime 目录：当未显式配置 `RUNTIME_DIR` 且未显式配置 `LOG_DIR` 时，默认解析到仓库根 `runtime`，从而让 API 默认日志落到仓库根 `runtime/logs/api`。
- 保持显式覆盖语义：`LOG_DIR` 仍最高优先级；非空显式 `RUNTIME_DIR` 仍用于推导 `RUNTIME_DIR/logs/api`；显式相对 `RUNTIME_DIR` 继续按进程 cwd 解析；缺失或空字符串 `RUNTIME_DIR` 视为未显式配置。
- 更新 README、环境变量模板、OpenSpec 和测试，说明按天轮转、3 天 access retention、默认 runtime 落点和生产持久卷建议。
- `stdout-only` 结构化日志模式作为本次非目标，后续如需容器 stdout 采集单独开 change。

## Capabilities

### New Capabilities

- `api-log-file-reduction-runtime-defaults`: API 日志文件日切分、access 默认保留期下调、默认 runtime 目录稳定解析到仓库根的行为契约。

### Modified Capabilities

- 无。

## Impact

- 代码：`packages/core/src/quantagent/core/config/settings.py`、`apps/api/src/quantagent/api/config/settings.py`、`apps/api/src/quantagent/api/observability/files.py`、`apps/api/src/quantagent/api/observability/maintenance.py`。
- 测试：`packages/core/tests/test_core.py`、`apps/api/src/tests/test_observability.py`，以及必要的 API 配置测试覆盖。
- 文档与模板：`apps/api/README.md`、根 `.env.example`、`apps/api/.env*.example`。
- 依赖：不新增运行时依赖，不引入外部日志平台，不改变 Docker Compose 服务拓扑。
- 安全：不提交真实 secret、日志文件、运行时数据库或私有配置；生产仍应通过显式 `RUNTIME_DIR` / `LOG_DIR` 指向持久卷。
