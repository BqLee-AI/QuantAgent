## 1. OpenSpec 评审与工程质量门槛

- [x] 1.1 提交 OpenSpec-only PR，只包含 `model-provider-config-minimal-v1` 的 proposal、design、spec、tasks 和必要元数据。
- [x] 1.2 在 PR 说明中链接 issue #156，并写清本 PR 只定义最小模型配置方案，不实现代码、不添加依赖、不改 API/Web/Core。
- [x] 1.3 运行 `openspec validate model-provider-config-minimal-v1 --type change --strict --json`。
- [x] 1.4 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。
- [x] 1.5 按工程质量门槛补强 design：目录蓝图、职责边界、核心字段、数据流、失败路径、复用取舍和验证入口必须可 review。

## 2. Core 数据、安全与外部适配边界

- [x] 2.1 在 `packages/core/src/quantagent/core/model_config/` 定义单个全局模型配置的领域类型、ORM model、service 和导出边界，字段覆盖 provider type、name、base URL、model、enabled、encrypted API key、key status、last error 和 updated timestamp。
- [x] 2.2 新增 Fernet 类 API key 加密 / 解密工具，主密钥从 `MODEL_CONFIG_ENCRYPTION_KEY` 读取，缺失或无效时返回安全配置错误。
- [x] 2.3 实现模型配置 service：保存时加密 key，查询时只返回 masked/configured/missing 状态，运行时短暂解密，状态推导不依赖 API DTO。
- [x] 2.4 新增独立 model invocation log 数据模型和迁移，记录 provider、model、status、prompt tokens、completion tokens、total tokens、error summary、request_id、trace_id、created_at 和可选 `agent_run_id`。
- [x] 2.5 通过 `FixedModelCallClient` port 隔离 OpenAI-compatible smoke 调用，测试和后续 AgentRuntime 可替换 provider client。
- [x] 2.6 为关键安全 / 协议适配边界补充短注释：secret 脱敏、固定 smoke prompt、provider 响应只解析 usage、不保存完整响应。

## 3. API / Contracts

- [x] 3.1 定义模型配置、保存请求、测试连接结果和 invocation summary 的 API DTO，避免直接返回 ORM model 或 core 内部对象。
- [x] 3.2 新增 `GET /api/v1/models/config`，返回统一 envelope 和脱敏后的全局配置状态。
- [x] 3.3 新增 `PUT /api/v1/models/config`，保存配置并加密 API key，响应不得回显 key 明文。
- [x] 3.4 新增 `POST /api/v1/models/actions/test-connection`，不接收 prompt，只发送固定 smoke prompt，并记录 invocation。
- [x] 3.5 新增 `GET /api/v1/models/invocations`，返回最近调用摘要和基础 token usage，limit 做服务端边界收敛。
- [x] 3.6 更新 `packages/contracts/schemas/` 的模型配置和 invocation JSON Schema，确保字段与 API/Web 使用一致。
- [x] 3.7 API route 保持薄层，只做鉴权、CSRF、DTO、envelope、错误映射和 mapper；核心流程不塞进 router。

## 4. Web `/models` 最小页面

- [x] 4.1 新增或补齐 `/models` 路由和导航入口，保持它独立于 Settings、插件配置和 runtime config。
- [x] 4.2 实现 `features/models/api.ts` 与 `queries.ts`，通过 shared API client 和 TanStack Query 管理服务端状态，页面不直接处理后端 envelope。
- [x] 4.3 route 文件只保留 TanStack Router 入口；模型配置表单、状态统计、invocation 表格和页面组合拆到 `features/models/components/`。
- [x] 4.4 UI 优先使用 HeroUI 表单控件、按钮、开关和表格，样式优先 Tailwind / 现有 token，避免为普通布局新增 CSS module。
- [x] 4.5 实现配置表单：provider type、显示名称、base URL、model、API key 写入式输入和 enabled；已配置 key 只展示 masked/configured 状态。
- [x] 4.6 实现测试连接按钮和 running / success / failed 状态，失败时展示安全错误摘要和 request id。
- [x] 4.7 展示最近 invocation 的 provider、model、status、prompt tokens、completion tokens、total tokens、created timestamp 和最近错误摘要，并覆盖 loading / empty / error / sensitive masked 状态。

## 5. 验证

- [x] 5.1 后端测试覆盖 key 加密入库、脱敏查询、运行时解密、缺主密钥错误、配置保存、配置查询和 invocation 记录。
- [x] 5.2 API 测试覆盖统一 envelope、写接口不回显 key、错误响应不泄露 key、disabled/missing_key/failed 状态和 OpenAPI 契约。
- [x] 5.3 前端测试覆盖 capability policy、模型错误摘要和 request id 展示；build 覆盖 route generation、HeroUI imports 和 TypeScript 契约。
- [x] 5.4 使用 mock provider 完成一次固定 prompt smoke 调用，并确认 token usage 可见，不使用真实 API key。
- [x] 5.5 运行与改动范围匹配的 Python、Web、OpenSpec 和 diff 检查，并在实现 PR 中记录结果。

## 6. 明确后续不混入本轮

- [x] 6.1 ProviderPolicy、fallback、budget、cost governance、自动模型发现和 LiteLLM Proxy 另开 issue / change。
- [x] 6.2 prompt 编辑器、AgentDefinition 编辑器、模型评估平台和多 provider 列表不进入本 V1。
- [x] 6.3 插件模型 key、普通 Settings 模型 key 和前端 runtime config 模型 key 不作为本 V1 的配置入口。
