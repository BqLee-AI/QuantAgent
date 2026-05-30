## Context

当前 API 日志实现来自 `add-api-structured-file-logging`，文件布局为 `LOG_DIR/{stream}/YYYY/MM/DD/{service}.{env}.{instance_id}.pid-{pid}.{stream}.{YYYYMMDDTHH}[.part-NNN].jsonl`。这个布局便于按小时排查，但在 `access` 高频写入、app 重启和多进程场景下会制造大量小文件；`#191` 已有压缩、retention 和 disk guard，但压缩只能降低字节数，不能显著降低文件数量和 inode 压力。

当前共享配置 `quantagent.core.config.settings.Settings.RUNTIME_DIR` 默认是相对路径 `runtime`。API 会把空 `LOG_DIR` 推导为 `RUNTIME_DIR / "logs" / "api"` 并 resolve。这样虽然启动后不会继续漂移，但从仓库根、`apps/api` 或其他 cwd 启动时，默认日志仍会落到不同 runtime 目录。本 change 修正默认落点，不取消显式配置。

本 change 依赖现有 API 私有 `observability` 模块，不重写 request context、formatter/filter、queue writer、disk guard、脱敏或审计边界。

## Goals / Non-Goals

**Goals:**

- 将 API 日志物理切分粒度从小时收敛为天，减少默认文件数量。
- 保留五个逻辑 stream 和 stream-specific retention。
- 保持大小轮转、`pid` 隔离、多进程避免覆盖和 maintenance 保守清理策略。
- 将未显式配置时的默认 `RUNTIME_DIR` 稳定到仓库根 `runtime`，让默认 `LOG_DIR` 稳定到仓库根 `runtime/logs/api`。
- 保持显式 `LOG_DIR` / `RUNTIME_DIR` 覆盖能力，尤其是生产持久卷路径。

**Non-Goals:**

- 不合并 `app/error/security` 物理文件，不新增 stream family。
- 不新增 `LOG_ROTATE_GRANULARITY`、`LOG_PHYSICAL_STREAM_MODE` 等配置。
- 不新增 stdout-only、OpenTelemetry、APM、collector 或外部日志服务。
- 不改变 API request context、结构化字段、脱敏规则、queue 降级或 disk guard 行为。
- 不把生产日志硬编码到仓库根目录；生产仍建议显式配置持久卷路径。

## Decisions

### 1. 文件时间片改为 day slice

`files.py` 中的文件名解析、构造和 writer 活跃切片从 hour slice 改为 day slice：

```text
{service}.{env}.{instance_id}.pid-{pid}.{stream}.{YYYYMMDD}[.part-NNN].jsonl
```

目录仍保持 `LOG_DIR/{stream}/YYYY/MM/DD/`，逻辑 stream 仍为 `access/app/error/security/audit`。同一 `{service, env, instance_id, pid, stream, date}` 活跃 writer 内小时变化不再切新文件；日期变化切新文件；大小超过 `LOG_ROTATE_MAX_BYTES` 时继续追加 `.part-NNN`。`pid` 继续保留，用于避免多进程或重启后覆盖同名活跃文件，因此同一天内重启或多进程仍可能产生多个不同 pid 的 base file。

实现应把 `ParsedLogFile.hour_slice/hour_start()`、writer 的 active hour 状态等内部命名重命名为 `date_slice/date_start()` 或等价 day/date 语义，避免后续维护误把日切分重新理解成小时切分；测试和文档必须使用 `YYYYMMDD`。

### 2. maintenance 按日期保护活跃文件

`maintenance.py` 中“当前切片不能被认为已关闭”的判断从 `now.strftime("%Y%m%dT%H")` 改为 `now.strftime("%Y%m%d")`。关闭文件压缩、retention 清理和 startup/shutdown 补偿仍只处理可确认关闭的文件：

- 当前日期文件默认跳过，除非 shutdown 传入 `force_closed_paths` 表示本进程已关闭该文件。
- 过期判断按文件日期起点与 retention cutoff 比较。
- 无法解析为新日切分命名的文件不纳入新 parser 的正常 maintenance 范围；本 change 不负责迁移旧小时文件。

### 3. 默认 access retention 改为 3 天

`Settings.LOG_ACCESS_RETENTION_DAYS` 默认值改为 3。环境模板和 README 同步更新。`apps/api/.env.test.example` 可继续使用更短测试默认值；production/staging 模板如不覆盖，应体现默认 3 天或说明按需显式加长。

### 4. 默认 runtime 只在未显式配置时锚定仓库根

`packages/core` 增加最小 helper，用于在未显式配置 `RUNTIME_DIR` 时探测仓库根：

- 从 `packages/core/src/quantagent/core/config/settings.py` 所在文件向上查找包含根 `pyproject.toml` 且存在 `apps/`、`packages/` 的目录。
- 找到时默认 `RUNTIME_DIR` 为 `<repo-root>/runtime`。
- 找不到时回退到 `Path("runtime")`，保持最小启动能力。

显式配置和空值语义如下：

- `LOG_DIR` 非空显式配置时，API 直接使用并 resolve；`LOG_DIR=` 空字符串继续视为未配置。
- `RUNTIME_DIR` 缺失或来自 constructor / dotenv / 环境变量的空字符串时，视为未显式配置，并进入仓库根探测默认值。
- `RUNTIME_DIR` 非空显式配置时，API 使用该值推导 `RUNTIME_DIR/logs/api`。
- 显式相对 `RUNTIME_DIR`（例如 `runtime`、`./runtime`、`../runtime`）继续按进程 cwd 解析，不强行改成仓库根相对路径。
- 本地 env example 如希望使用仓库根默认落点，应删除 `RUNTIME_DIR` 或写成 `RUNTIME_DIR=`；生产 / staging 模板如需要容器持久卷，应继续非空显式写 `/app/runtime` 或其他部署路径。

实现时可通过 `Settings.model_fields_set` 或等价 Pydantic v2 机制判断 `RUNTIME_DIR` 是否由调用方 / dotenv / 环境显式提供，但必须先把空字符串归一化为未配置，避免 `RUNTIME_DIR=` 被 Pydantic `Path` 解析为当前目录 `.`。这个判断属于配置边界，需用短中文注释说明是为了避免“默认值漂移”和“显式配置改义”混淆。

### 5. 文档表达本地默认和生产建议

README 和 `.env*.example` 应明确：

- 留空 `RUNTIME_DIR` / `LOG_DIR` 时，本地源码运行默认写到仓库根 `runtime/logs/api`。
- 非空相对 `RUNTIME_DIR` 仍按进程 cwd 解析；只有缺失或空字符串才进入仓库根默认探测。
- 生产、容器或 systemd 部署建议显式设置 `RUNTIME_DIR` 或 `LOG_DIR` 到持久卷路径，例如 `/app/runtime` 或 `/var/lib/quantagent/runtime`。
- 不能提交真实日志、运行时数据、secret 或私有配置。

## Risks / Trade-offs

- [Risk] 旧小时日志文件不再被新 parser 识别，导致旧文件 retention 不处理。→ Mitigation：本 change 不做历史迁移；PR 说明中提示旧文件可手动清理或另开迁移清理任务。
- [Risk] 日切分会让单个文件更大。→ Mitigation：保留 `LOG_ROTATE_MAX_BYTES` 大小轮转和 `.part-NNN`。
- [Risk] 仓库根探测失败时默认仍可能按 cwd。→ Mitigation：源码部署路径下用文件向上探测；非源码安装场景可显式配置 `RUNTIME_DIR`。
- [Risk] 错误判断显式 `RUNTIME_DIR` 会改变相对配置语义。→ Mitigation：测试覆盖未显式、显式绝对、显式相对三类。

## Validation Strategy

- OpenSpec strict validate 本 change。
- Core 单元测试覆盖未提供 runtime、空字符串 runtime、显式绝对 runtime、显式相对 runtime 和 `DATABASE_URL` 仍可为空。
- API observability 测试覆盖日命名、同日不按小时轮转、跨日轮转、大小轮转、parser、压缩、retention 和 active file skip。
- API 全量 unittest 确认日志改动不破坏 request context、auth/security、DB readiness 和现有 route 行为。
