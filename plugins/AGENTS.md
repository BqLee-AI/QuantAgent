# AGENTS.md

## 定位

- `plugins` 存放随代码分发的官方插件，不存放第三方、社区、私有或运行时安装插件。
- 运行时安装插件应放在 `runtime/plugins`，并通过 Registry 进入系统。
- 本目录的规则来自 `docs/design/03-plugin-system-and-registry.md`、`06-source-plugin-design.md`、`07-industry-package-design.md` 和 `11-crawler-source-plugin-boundary.md`。

## 行为约束

- 涉及 `plugins/**` 的规划、实现和 review 必须读取 `.agents/skills/references/core-and-plugin-architecture-gate.md`，把目标分层落实到 issue、OpenSpec、实现计划或 PR 说明。
- 官方插件必须通过 `plugin.yaml` 注册，禁止靠核心代码硬编码 class、import 列表或 if/else 注册。
- 插件 ID 使用 `quantagent.official.*` 命名空间，并声明版本。
- 插件配置 schema 不得包含真实 secret；敏感字段使用 secret reference。
- 插件开发者只声明插件能力和 `config.schema.json` 配置契约；配置校验、保存、启停、调度、审计和生命周期由平台负责。
- Source Plugin 只负责采集、接收和标准化原始信息，不能直接调用行业包。
- Source Plugin 只消费平台传入的 DTO / `effective_config` 并返回平台约定的 source 输出结构，不负责 `RawEvent` 入库、去重、`SourceBinding`、`Event Bus`、权限或生命周期托管。
- Industry Plugin 可以提供 AgentDefinition、Skill、工具、market mapping 和 scoring hints，但不能绕过 AgentRuntime、ToolRegistry、Skill Registry 或 Decision。
- Broker Plugin 初版必须默认禁用真实执行，只允许 disabled、dry-run 或 mock 路径。
- 插件安装、升级、降级、启停、reload、配置变更和执行错误需要可审计。

## 局部规则

- 新增官方插件前先确认对应 issue、OpenSpec 或设计文档真源。
- 新增插件时同时考虑 manifest、config schema、README、最小测试和运行时审计边界。
- 对网页或新闻类抓取插件，默认考虑 `Readability` 和 `Jina Reader` 两类读取路径；是否作为插件内部策略或复用官方 reader 插件，应在 issue 或设计文档中写清。
- 私有关键词、私有行业逻辑、交易策略偏好和付费 API key 不进入本目录。
