## ADDED Requirements

### Requirement: Official Tavily Source/Data Tool Plugin Package

系统 MUST 支持一个官方 `Tavily` Source/Data Tool Plugin，作为 `plugins/sources/` 下可分发的官方插件包交付。

#### Scenario: Official plugin package includes minimum deliverables

- **GIVEN** 仓库需要新增官方 `Tavily` evidence tool 能力
- **WHEN** 实现者按本 change 落地插件包
- **THEN** 插件包 MUST 包含 `plugin.yaml`、`config.schema.json`、README、入口实现、Tavily client adapter、最小测试和静态 fixture
- **AND** 插件 MUST 通过 `plugin.yaml` 注册为 `source` 类型官方插件
- **AND** 插件 `id` MUST 为 `quantagent.official.source.tavily`
- **AND** 插件 `capabilities` MUST 至少声明 `source.fetch`
- **AND** 插件 MAY 兼容声明 `source.search` 与 `source.extract` 作为细分调用语义

### Requirement: Tavily Plugin Exposes Source Fetch Contract In V1

`Tavily` 插件第一版 MUST 对齐 `source` 插件的 `SourceFetchResult` 契约，并通过 `source.fetch` 提供统一入口。

#### Scenario: Source fetch routes to search path when query is provided

- **GIVEN** 运行时通过 `source.fetch` 调用 Tavily
- **WHEN** 插件收到合法 `query` 和可选搜索参数
- **THEN** 插件 MUST 走搜索路径执行
- **AND** 输出 MUST 可被 `SourceFetchResult` 解析
- **AND** 输出项 SHOULD 至少保留 `title`、`url`、`content` 和来源相关字段

#### Scenario: Source fetch routes to extract path when url is provided

- **GIVEN** 运行时通过 `source.fetch` 调用 Tavily
- **WHEN** 插件收到合法 `url` 和可选抽取参数
- **THEN** 插件 MUST 走提取路径执行
- **AND** 输出 MUST 可被 `SourceFetchResult` 解析
- **AND** 输出项 MAY 通过 `metadata` 保留 `raw_content`、`favicon_url`、`error` 等补充字段

#### Scenario: Search capability returns structured search results

- **GIVEN** 运行时通过受控工具边界调用 Tavily `search`
- **WHEN** 插件收到合法 query 和可选搜索参数
- **THEN** 插件 MUST 返回结构化搜索结果列表
- **AND** 每条结果 SHOULD 至少包含 `title`、`url`、`content`、`score` 和来源相关字段
- **AND** 输出 MUST 是 JSON-safe、可序列化、可被 `SourceFetchResult` 校验的 DTO

#### Scenario: Extract capability returns structured page content

- **GIVEN** 运行时通过受控工具边界调用 Tavily `extract`
- **WHEN** 插件收到合法 URL 和可选抽取参数
- **THEN** 插件 MUST 返回结构化正文抽取结果
- **AND** 输出 SHOULD 至少包含 `title`、`content`、`canonical_url` 或等价链接字段
- **AND** 输出 MAY 包含 `raw_content`、`summary`、`published_at` 等补充字段
- **AND** 输出 MUST 是 JSON-safe、可序列化、可被 `SourceFetchResult` 校验的 DTO

#### Scenario: V1 defers other Tavily capabilities

- **WHEN** Tavily 插件第一版被评审
- **THEN** `crawl`、`map`、`research`、多步 agent workflow 或插件编排能力 MUST 不进入本轮
- **AND** 如需扩展这些能力，必须由后续 OpenSpec change 单独批准

### Requirement: Tavily Plugin Consumes Platform-Validated Config

`Tavily` 插件 MUST 只消费平台传入的校验后配置 DTO / `effective_config`，不负责 secret 发现、配置保存或运行时治理。

#### Scenario: Plugin receives injected configuration only

- **GIVEN** 平台已经完成 config schema 校验和 secret reference 解析
- **WHEN** Runtime 调用 Tavily 插件
- **THEN** 插件 MUST 只读取 runtime 注入的只读配置
- **AND** 插件 MAY 消费 `api_key_ref` 对应的已注入安全值、`timeout_seconds`、默认结果数和其他必要参数
- **AND** 插件 MUST NOT 自行读取数据库、内部 service、未治理的本地私有配置或宿主 secret resolver

### Requirement: Tavily Plugin Uses Runtime Protocol Boundary

`Tavily` 插件 entrypoint MUST 满足 runtime 统一协议边界，而不是依赖核心代码硬编码某个实现类型。

#### Scenario: Runtime accepts protocol-shaped Tavily plugin

- **GIVEN** Runtime 通过 manifest `entrypoint` 加载 Tavily 插件
- **WHEN** entrypoint 返回满足 `RuntimePlugin` 协议的对象
- **THEN** Runtime MUST 能调用该插件对象
- **AND** OpenSpec MUST NOT 要求插件必须通过核心代码硬编码注册
- **AND** OpenSpec MUST NOT 要求插件必须依赖唯一的宿主继承层级才能接入

#### Scenario: BasePlugin remains an optional convenience layer

- **WHEN** 官方 Tavily 插件需要减少 lifecycle 样板代码
- **THEN** 实现 MAY 继承轻量 `BasePlugin`
- **AND** 该继承只作为便利层
- **AND** 插件的宿主接入约束仍然是统一 runtime 协议而不是具体基类

### Requirement: Tavily Third-Party API Is Isolated Behind A Client Adapter

`Tavily` 第三方 API / SDK 适配 MUST 被隔离到独立 client adapter，而不是散落在插件入口逻辑中。

#### Scenario: Plugin entrypoint delegates Tavily transport details to adapter

- **GIVEN** 插件实现 Tavily `search` 或 `extract`
- **WHEN** 插件处理 capability 调用
- **THEN** 插件入口负责 capability 分发、输入校验和输出组装
- **AND** Tavily HTTP / SDK 调用、错误包装和字段归一化 MUST 下沉到独立 adapter / client
- **AND** 实现 MUST NOT 把第三方协议细节散落在多个入口方法中

### Requirement: Tavily Plugin Boundary Excludes Runtime Or Plugin Orchestration Responsibilities

`Tavily` 插件 MUST NOT 承担插件编排、事件链路或核心运行时职责。

#### Scenario: Tavily remains a controlled evidence tool provider

- **GIVEN** 其他插件、Agent 或后续 ToolRegistry 需要 Tavily 能力
- **WHEN** 审查 Tavily 插件职责
- **THEN** Tavily MUST 只提供 `search` / `extract` 能力和结构化结果
- **AND** Tavily MUST NOT 直接 import 或调用 RSS、Readability、Discord、Binance 或其他插件实现
- **AND** Tavily MUST NOT 负责 ToolRegistry、Plugin Runtime、RawEvent 入库、Event Bus、审计、审批或调度

### Requirement: Tavily Plugin Tests Must Be Network-Free

`Tavily` 插件验证 MUST 采用不依赖真实外部网络的最小 harness。

#### Scenario: Search and extract tests use fixtures or fake client

- **GIVEN** 实现者为 Tavily 插件补测试
- **WHEN** 测试 `search` / `extract` 行为
- **THEN** 测试 MUST 使用静态响应 fixture、fake client 或等价 mock 路径
- **AND** 测试 MUST NOT 依赖真实 Tavily API key
- **AND** 测试 MUST NOT 依赖外部网络稳定性

#### Scenario: Failure paths are validated with structured errors

- **WHEN** 插件配置缺失、capability 不支持、上游超时或 DTO 校验失败
- **THEN** 测试 MUST 证明插件返回结构化且脱敏的失败结果
- **AND** 测试 MUST NOT 断言真实 secret、token 或原始外部异常文本泄露到用户侧输出
