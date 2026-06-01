## observability

`observability/` 负责 `apps/api` 的 API 私有结构化日志基础设施，只处理 HTTP 传输层可观测性。

当前目录职责：

- `context.py`：请求上下文、`request_id` / `trace_id` / actor context。
- `events.py`：稳定 event 名称常量。
- `formatters.py`：JSON Lines 格式化。
- `filters.py`：上下文字段注入与敏感字段脱敏。
- `files.py`：stream 文件布局、按日命名与大小轮转。
- `maintenance.py`：按当前 UTC 日期保护可能活跃文件，并处理关闭文件压缩、retention 清理、启动补偿和磁盘水位保护。
- `queue.py`：队列化写入、降级与 shutdown drain。
- `logging.py`：日志 bootstrap、logger helper、FastAPI 接入点。

不要把以下能力放进这里：

- 业务审计真源、数据库 `audit_logs` 持久化。
- route 业务逻辑、权限规则、插件 registry、数据库领域流程。
- OpenTelemetry / 外部 APM / collector 接入。
