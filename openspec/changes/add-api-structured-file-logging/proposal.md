## Why

`apps/api` 当前只有零散 `logging.getLogger("quantagent.api")` 使用，缺少统一的结构化字段、请求上下文、脱敏规则、文件落盘和高流量文件管理策略。随着 API v1 route、鉴权、钱包查询、插件配置和后续高风险动作逐步增加，如果继续让各模块临时写日志，会导致 request_id / trace_id 无法串联、敏感信息泄露、access 日志淹没错误与安全事件、日志文件归档和清理不可控。

维护者已确认首版日志数据落文件、不存数据库。本 change 需要把 API 传输层的结构化文件日志闭环收束为可 review、可测试、可分阶段实现的 OpenSpec 真源。

## What Changes

- 在 `apps/api` 引入 API 私有 observability/logging 能力，用于日志初始化、请求上下文、结构化 JSON Lines 输出、脱敏、队列化写入、文件分类、轮转和 maintenance。
- 将现有 `X-Request-ID` 能力扩展为 request context，补齐 `trace_id`，并保证响应 header、错误 envelope 和日志字段一致。
- 将日志数据写入 `LOG_DIR/{stream}/YYYY/MM/DD/*.jsonl`，其中 `LOG_DIR` 默认解析为 `RUNTIME_DIR/logs/api`，stream 至少包括 `access`、`app`、`error`、`security`、`audit`。
- 使用 `{service}.{env}.{instance_id}.pid-{pid}.{stream}.{YYYYMMDDTHH}[.part-NNN].jsonl` 命名活跃文件和轮转文件，避免多进程写同一个文件。
- 阶段 1 即采用队列化写入，避免普通请求路径直接承担文件 IO；阶段 2 补充关闭文件压缩、按 stream retention、启动补偿清理和磁盘水位保护。
- 更新 `apps/api` README、环境变量样例和测试，说明日志配置、文件布局、轮转、压缩、保留和降级策略。

## Capabilities

### New Capabilities

- `api-structured-file-logging`: 定义 `apps/api` 结构化文件日志、请求追踪上下文、stream 分类、文件轮转、队列化写入、脱敏、maintenance 和验证要求。

### Modified Capabilities

- 无。

## Impact

- 影响 `apps/api` HTTP 传输层基础设施：`main.py`、HTTP middleware、异常处理、DB readiness/session 失败路径、auth/security 事件和 README。
- 新增 API 私有模块：`apps/api/src/quantagent/api/observability/`。
- 新增或扩展 API 专属配置项：日志目录、实例 ID、轮转阈值、队列大小、maintenance 安全窗口、磁盘水位、按 stream retention、access 降级开关。
- 不改变业务 API route 契约，不新增数据库表，不引入外部日志平台、OpenTelemetry 或 `packages/core` 共享 observability 抽象。
