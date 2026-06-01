# Tasks: API 结构化文件日志闭环

## 1. OpenSpec 与实现前审核

- [x] 1.1 校验本 change 的 `proposal.md`、`design.md`、`specs/api-structured-file-logging/spec.md` 和 `tasks.md` 是否覆盖 #180 的文件落盘、两阶段实现和 OpenSpec-only PR 边界。
- [x] 1.2 运行 `openspec validate add-api-structured-file-logging --type change --strict --json`。
- [x] 1.3 创建只包含本 change OpenSpec artifacts 的 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入实现。

## 2. 阶段 1：核心日志基础设施

- [x] 2.1 在 `apps/api/src/quantagent/api/observability/` 新增 API 私有模块，建立 context、logging bootstrap、formatter、filter、file writer、queue writer、events 的职责边界，不修改 route 业务逻辑。
- [x] 2.2 实现幂等 `configure_api_logging(settings)`，在 `create_app()` 中显式调用，并确保测试多次创建 app 不重复注册 handler。
- [x] 2.2a 在 FastAPI lifespan shutdown 阶段接入幂等 logging shutdown，停止 queue listener、flush 已入队记录并关闭文件 handler，避免测试和进程退出遗留后台线程或文件描述符。
- [x] 2.3 扩展 API settings 和 env example，增加 `LOG_DIR`、`LOG_INSTANCE_ID`、`LOG_ROTATE_MAX_BYTES`、`LOG_QUEUE_MAX_SIZE`、`LOG_ACCESS_DROP_WHEN_FULL` 等阶段 1 必需配置，并明确 `LOG_DIR` 默认解析为 `RUNTIME_DIR/logs/api`；日志格式固定为 JSON Lines，不提供多格式切换配置。
- [x] 2.4 实现 JSON Lines formatter 和上下文字段注入，确保每条记录一行 JSON，包含 service、env、instance_id、pid、stream、event、request_id、trace_id 等稳定字段。
- [x] 2.5 实现敏感字段脱敏 filter，覆盖 authorization、cookie、csrf、password、token、secret、session、api key、database URL 等字段或 header。

## 3. 阶段 1：请求上下文与日志接入

- [x] 3.1 将现有 request id middleware 演进为 request context middleware，统一 `X-Request-ID`、`X-Trace-ID`、`traceparent` 解析、响应 header 回写和 context 清理。
- [x] 3.2 更新异常处理器，把 `trace_id` 写入错误 envelope，并让未处理异常输出脱敏 `error` stream 事件。
- [x] 3.3 接入 HTTP access log，确保每个请求只产生一条 API 结构化 access 记录，并关闭或覆盖 `uvicorn.access` 的重复输出。
- [x] 3.4 接入 DB 初始化、session 创建失败、readiness 失败日志，使用稳定 event 名称并写入 `app` 或 `error` stream。
- [x] 3.5 接入 auth/security 失败路径和 actor audit context，确保 CSRF、未授权、禁止访问等事件写入 `security` stream，受保护写操作上下文可写入 `audit` stream。

## 4. 阶段 1：文件布局、轮转与队列写入

- [x] 4.1 实现 stream 到文件目录的映射：`LOG_DIR/{stream}/YYYY/MM/DD/`，支持 `access`、`app`、`error`、`security`、`audit`，默认 `LOG_DIR` 来自 `RUNTIME_DIR/logs/api`。日志模块初始化时应对 `LOG_DIR` 执行绝对路径解析，避免相对 `RUNTIME_DIR` 随 cwd 变化漂移。
- [x] 4.2 实现文件命名：`{service}.{env}.{instance_id}.pid-{pid}.{stream}.{YYYYMMDDTHH}[.part-NNN].jsonl`，并统一目录日期占位符为 `YYYY/MM/DD`、文件小时分片占位符为 `YYYYMMDDTHH`。
- [x] 4.3 实现小时轮转和大小轮转，超过大小阈值时切换到下一个 `part-NNN`。
- [x] 4.4 实现阶段 1 队列化写入，普通请求路径只构造记录并入队，由后台 listener 写入文件。
- [x] 4.5 实现队列满降级策略：access 可丢弃、采样或聚合计数，error/security/audit 尽量保留；关键 stream 入队失败时走受限 fallback 或至少输出一次脱敏 stderr warning，且不得递归写日志或无限阻塞。
- [x] 4.6 确保多进程通过 `pid` 写独立活跃文件，不依赖跨进程锁写同一个文件。

## 5. 阶段 1：测试与文档

- [x] 5.1 补充 request_id / trace_id 一致性测试，覆盖 header、错误 envelope 和日志记录。
- [x] 5.2 补充 JSONL formatter、脱敏 filter、access/error/security/audit stream 分类测试。
- [x] 5.3 补充文件目录、文件命名、小时轮转、大小轮转和 part 编号测试，所有文件写入测试使用临时目录。
- [x] 5.4 补充队列写入和队列满降级测试，验证 access 降级不影响 error/security/audit 的尽量保留策略。
- [x] 5.4a 补充 logging shutdown 测试，验证 listener 可停止、已入队记录尽量 flush、重复创建/关闭 app 不遗留后台线程、重复 handler 或未关闭文件描述符。
- [x] 5.5 更新 `apps/api/README.md`、根 `.env.example`、`apps/api/.env.example` 和 `apps/api/.env.*.example` 多环境模板，说明阶段 1 支持的日志配置、文件布局、命名、轮转、脱敏和非目标。
- [x] 5.6 运行 `cd apps/api && uv run python -m unittest discover -s src`，并在实现 PR 中说明阶段 1 验证结果。

## 6. 阶段 1 Review Gate

- [x] 6.1 确认阶段 1 已能独立运行、独立测试、独立 review，不依赖阶段 2 才形成核心日志闭环。
- [x] 6.2 确认 route 函数没有承担日志 JSON 拼接、脱敏、文件路径、轮转或队列管理逻辑。
- [x] 6.3 确认阶段 1 契约已经稳定：request context、formatter、redaction、stream 分类、文件命名、小时/大小轮转和队列写入边界。

## 7. 阶段 2：Maintenance 与磁盘保护

- [x] 7.1 实现只处理关闭文件的 `.jsonl.gz` 压缩，禁止压缩或清理活跃文件，且不在请求路径执行压缩；无法确认关闭状态的文件必须跳过。
- [x] 7.2 实现按 stream retention 清理，允许 access 短保留，error/security/audit 长保留。
- [x] 7.3 实现启动时补偿清理，处理上次退出后遗留的未压缩关闭文件和已过期文件。
- [x] 7.4 实现磁盘水位保护，支持 `LOG_MAX_TOTAL_BYTES`、`LOG_MIN_FREE_BYTES`、`LOG_ACCESS_DROP_WHEN_FULL`、`LOG_MAINTENANCE_MIN_AGE_SECONDS` 或等价配置。
- [x] 7.5 实现磁盘压力下降级策略：优先停止或降采样 access 写入，保留 error/security/audit 写入能力，并至少输出一次脱敏 stderr warning。

## 8. 阶段 2：测试、文档与最终收口

- [x] 8.1 补充关闭文件压缩测试，验证活跃文件不会被压缩、删除或重写，无法确认关闭状态的文件会被跳过。
- [x] 8.2 补充按 stream retention 清理测试和启动补偿清理测试。
- [x] 8.3 补充磁盘水位保护和 access 降级测试，验证关键 stream 尽量保留。
- [x] 8.4 更新 README、根 `.env.example`、`apps/api/.env.example` 和 `apps/api/.env.*.example` 多环境模板，补充压缩、retention、补偿清理、磁盘保护和阶段 2 运维说明。
- [x] 8.5 运行 `cd apps/api && uv run python -m unittest discover -s src`。
- [x] 8.6 最终 PR 描述更新为完整交付范围、两阶段提交边界、验证结果、未验证风险和非目标。
