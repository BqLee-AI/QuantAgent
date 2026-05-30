# Tasks: 减少 API 日志文件数量并稳定 runtime 默认路径

## 1. OpenSpec Review Gate

- [x] 1.1 确认 `proposal.md`、`design.md`、`specs/api-log-file-reduction-runtime-defaults/spec.md` 覆盖按天切分、access 3 天 retention、runtime 默认仓库根、显式覆盖兼容和 stdout-only 非目标。
- [x] 1.2 运行 `openspec validate reduce-api-log-files-and-stabilize-runtime-defaults --type change --strict --json`。

## 2. Core runtime 默认路径

- [x] 2.1 在 `packages/core/src/quantagent/core/config/settings.py` 增加缺失或空字符串 `RUNTIME_DIR` 时的仓库根探测默认值；保持非空显式绝对和非空显式相对 `RUNTIME_DIR` 语义不变。
- [x] 2.2 补充 `packages/core/tests/test_core.py`，覆盖未显式默认仓库根、空字符串默认仓库根、显式绝对、显式相对和 `DATABASE_URL` 为空。

## 3. API 日志日切分

- [x] 3.1 更新 `apps/api/src/quantagent/api/observability/files.py`，将文件命名、解析、活跃切片和跨切片轮转从 `YYYYMMDDTHH` 改为 `YYYYMMDD`，并把内部 hour 命名收敛为 day/date 语义。
- [x] 3.2 更新 `apps/api/src/quantagent/api/observability/maintenance.py`，按当前 UTC 日期保护可能活跃文件，并保持 shutdown force-closed 补偿路径。
- [x] 3.3 将 `apps/api/src/quantagent/api/config/settings.py` 中 `LOG_ACCESS_RETENTION_DAYS` 默认值改为 3，其他 stream retention 默认值不变。

## 4. 文档与模板

- [x] 4.1 更新 `apps/api/README.md` 的日志路径、文件命名、轮转、retention 和 runtime 默认落点说明。
- [x] 4.2 更新根 `.env.example` 与 `apps/api/.env*.example`，说明 `RUNTIME_DIR` / `LOG_DIR` 留空默认仓库根 runtime、非空相对 `RUNTIME_DIR` 保持 cwd-relative、生产建议显式持久卷路径，并把 access retention 默认展示为 3。
- [x] 4.3 检查并按需更新 `apps/api/src/quantagent/api/observability/README.md`，确保模块职责说明不保留小时切分或旧 maintenance 语义。

## 5. 测试与验证

- [x] 5.1 更新 `apps/api/src/tests/test_observability.py`，覆盖日命名、同日跨小时不切文件、跨日切文件、大小轮转、parser、压缩、retention 和 active file skip。
- [x] 5.2 运行 `uv run python -m unittest packages.core.tests.test_core`。
- [x] 5.3 运行 `cd apps/api && uv run python -m unittest src.tests.test_observability`。
- [x] 5.4 运行 `cd apps/api && uv run python -m unittest discover -s src`。
- [x] 5.5 再次运行 `openspec validate reduce-api-log-files-and-stabilize-runtime-defaults --type change --strict --json`，确认 artifacts 与实现一致。
