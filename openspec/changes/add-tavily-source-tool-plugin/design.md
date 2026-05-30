## Context

当前 QuantAgent 对插件运行时的真源已经比较清楚：

- Registry 通过 `plugin.yaml` 发现插件，不硬编码 import。
- Runtime 通过 manifest `entrypoint` 加载插件实例。
- Runtime 接受两类插件形态：
  - 继承 `packages/plugin-sdk` 提供的轻量 `BasePlugin`
  - 只满足 `RuntimePlugin` 协议形状的对象
- Runtime 当前不会强制插件必须继承某个基类，只要求对象具备 `load/start/stop/health_check/invoke` 五个统一方法。
- `RuntimeContext` 是受控上下文，只暴露 `plugin_id`、`version`、`request_id`、只读 `config`、`metadata` 和 `logger`，不暴露 DB、scheduler、Event Bus、内部 service 或 secret resolver。

同时，`official-plugin-v1-main-chain` 已经明确：

- Tavily 是 evidence source/data tool，不是编排器。
- 第一版只做 `search` / `extract`。
- 其他插件或 Agent 之后只能通过 Plugin Runtime / ToolRegistry 调用这些能力。

因此，这个 change 不重新定义 runtime，也不实现完整 ToolRegistry，而是把 Tavily 插件本身的边界、目录规划、接入方式、schema 和验证方式写清楚。

## Goals / Non-Goals

**Goals:**

- 定义官方 `Tavily` Source/Data Tool Plugin 的最小插件包蓝图。
- 固定第一版 capability 只包含 `search` / `extract`。
- 固定工具 ID、输入输出 schema 和 README 说明方式。
- 明确第三方 Tavily API 适配应下沉到独立 adapter/client，而不是散落在插件入口。
- 对“基类继承 vs 协议接入”做显式取舍，给实现阶段一个稳定方向。
- 定义最小测试与验证策略，避免依赖真实外部网络。

**Non-Goals:**

- 不实现 ToolRegistry 核心。
- 不实现 Plugin Runtime 核心。
- 不实现数据库、RawEvent 入库、Event Bus、审计表、Scheduler 或 SourceBinding。
- 不实现 Tavily 的 `crawl`、`map`、`research`、多步 agent workflow 或插件编排能力。
- 不让 Tavily 直接 import 或调用 RSS、Readability、Discord、Binance 或其他插件。
- 不处理真实 secret 存储、控制台配置 UI 或 schema-driven form 落地。

## Directory / File Plan

实现阶段的目标目录规划如下：

```text
plugins/sources/tavily-source/
  README.md
  plugin.yaml
  config.schema.json
  src/
    tavily_source.py
    tavily_client.py
    schemas.py
  tests/
    test_tavily_source.py
    fixtures/
      tavily_search_response.json
      tavily_extract_response.json
```

各文件职责：

- `plugin.yaml`
  - 声明插件 ID、版本、类型、entrypoint、capabilities 和 config schema 位置。
- `config.schema.json`
  - 声明插件级配置字段，例如 `api_key_ref`、`timeout_seconds`、`default_max_results`、`default_extract_depth`。
- `README.md`
  - 说明 Tavily 在官方插件主链路中的定位、非目标、capability 列表、最小配置和测试方式。
- `src/tavily_source.py`
  - 插件入口；负责 capability 分发、输入 DTO 校验、调用 adapter、输出 DTO 组装。
- `src/tavily_client.py`
  - Tavily 第三方适配层；负责 HTTP / SDK 请求、超时、错误包装和响应字段归一化。
- `src/schemas.py`
  - 插件内 search/extract 的输入输出 schema 草案、字段转换和复用常量。
- `tests/test_tavily_source.py`
  - 覆盖 `search` / `extract` 成功、配置缺失、capability 不支持、上游错误和 schema 校验失败。
- `tests/fixtures/*.json`
  - 保存 Tavily API 的静态样例响应，避免测试依赖真实外网。

## Decisions

### Decision 1: Tavily 作为 source/data tool 插件，只暴露 `search` / `extract`

第一版 capability 固定为：

- `source.search`
- `source.extract`

对应官方工具 ID：

- `quantagent.official.source.tavily.search`
- `quantagent.official.source.tavily.extract`

原因：

- `official-plugin-v1-main-chain` 已明确 Tavily 第一版边界。
- `search` 对应主动检索外部证据。
- `extract` 对应对已知 URL 做高质量正文抽取。
- `crawl` / `map` / `research` 会迅速把范围扩成“通用网络 agent”，不适合本轮。

### Decision 2: 接入方式采用“协议优先，可选复用 BasePlugin”

本轮推荐实现方式：

- 插件 entrypoint 返回满足 `RuntimePlugin` 协议的对象
- 实现代码可以继承 `BasePlugin` 以减少样板代码
- 但 OpenSpec 不要求 Tavily 必须依赖继承才能接入 runtime

结论：**协议是接入约束，`BasePlugin` 是可选便利层。**

原因：

- 当前 `PluginRuntimeService` 已明确支持 structural protocol；这不是假设，而是仓库现状。
- `BasePlugin` 提供受控 context 保存、默认 lifecycle no-op 和统一 logger 访问，适合减少插件样板代码。
- 如果把“必须继承基类”写成强约束，会增加插件作者对 SDK 内部实现的耦合，也会让简单工具插件的测试替身变重。
- 业内最佳实践上，宿主侧通常依赖稳定协议/接口而不是具体继承层级；基类更适合作为 convenience layer，而不是唯一接入门槛。

对比：

**基类继承优点：**

- 默认 lifecycle 行为已提供，样板更少。
- `context`、`logger` 获取更统一。
- 对仓库内官方插件实现风格更容易保持一致。

**基类继承缺点：**

- 插件与 SDK 基类耦合更强。
- 对纯能力插件或轻量 mock/fake 测试不够轻。
- 后续若想让非 Python class/factory 风格的实现接入，弹性较差。

**协议接入优点：**

- 宿主只依赖能力形状，耦合更小。
- 更利于单元测试、fake plugin 和最小 adapter 封装。
- 更符合 runtime 当前已支持的结构化接入方式。

**协议接入缺点：**

- 没有默认实现时，插件作者需要自己补 lifecycle 样板。
- 如果不同插件完全自由发挥，代码风格可能分散。

因此本轮建议：

- 规范层面要求满足 `RuntimePlugin` 协议
- 官方实现默认可继承 `BasePlugin`
- Runtime 与 OpenSpec 都不把 `BasePlugin` 上升为唯一合法接入方式

### Decision 3: Tavily 第三方集成必须隔离到独立 client adapter

`src/tavily_client.py` 作为独立适配层，负责：

- 构造 Tavily 请求
- 注入 API key / timeout / 默认参数
- 将第三方错误转换为插件侧可包装的异常
- 归一化 Tavily search / extract 返回字段

插件入口 `src/tavily_source.py` 不直接：

- 拼接原始 Tavily URL
- 散落处理 HTTP headers / retries / timeout
- 直接依赖第三方响应的每个嵌套字段

原因：

- 避免入口文件同时承载 runtime、DTO 校验和第三方协议适配。
- 后续如果 Tavily SDK 版本变化，只需局部调整 adapter。
- 便于 fixture/mock 测试替换 client，而不是 mock 整个 runtime。

### Decision 4: 配置通过 schema 和 runtime context 注入，不允许插件自行发现 secret

最小配置字段草案：

- `api_key_ref`: `string`
- `timeout_seconds`: `number`, optional
- `default_max_results`: `integer`, optional
- `default_search_depth`: `string`, optional
- `include_favicon`: `boolean`, optional
- `include_raw_content`: `boolean`, optional

插件运行时消费：

- `self.context.config` 或等价只读 config 映射

插件不负责：

- 从环境变量直接读取真实 key
- 自己查数据库或内部 secret storage
- 保存、更新或缓存用户配置

原因：

- 这符合 `packages/core/AGENTS.md` 对 RuntimeContext 的限制。
- 也符合 plugin runtime v1 的“平台校验后注入 config”边界。

### Decision 5: `search` / `extract` 输出先使用 JSON-safe tool DTO，不复用 `SourceFetchResult`

虽然 Tavily 被归类在 `source/data tool` 范畴，但本轮两个 capability 都是“工具式调用”而不是“直接产出 RawEvent candidate”。因此输出不强行贴 `SourceFetchResult`，而是定义插件内统一 JSON-safe tool DTO。

`search` 输出字段草案：

```text
query
results[]
  title
  url
  snippet
  score
  source
  published_at?
  favicon_url?
metadata
  provider
  result_count
  search_depth?
```

`extract` 输出字段草案：

```text
url
title
content
raw_content?
summary?
canonical_url?
published_at?
metadata
  provider
  content_length
  extraction_source?
```

原因：

- `SourceFetchResult` 面向 source item 列表，更适合 RSS/reader 这类事件候选输出。
- Tavily `search` 更像 evidence query result，不应伪装成 source fetch item。
- 强行复用错误 DTO 会让字段语义扭曲，后续 ToolRegistry 统一时反而更难收敛。
- 但 DTO 仍必须保持 JSON-safe、schema 可校验和 runtime 可序列化。

### Decision 6: 测试以静态 fixture + fake client 为主，不依赖外部网络

测试入口优先覆盖：

- `search` 成功返回结构化结果
- `extract` 成功返回正文抽取结果
- 缺少 `api_key_ref` 或 runtime 未注入配置时失败
- 未声明 capability 时 runtime 返回结构化错误
- Tavily 上游超时或 4xx/5xx 被包装成脱敏错误
- DTO 非法字段会在插件内被拒绝

测试不依赖：

- 真实 Tavily API key
- 真实外部网络
- ToolRegistry / API / DB / Event Bus

## Data Flow

`search` 调用链：

```text
Runtime / ToolRegistry
  -> plugin.invoke(capability="source.search", input={query, max_results, ...})
  -> TavilySourcePlugin
  -> TavilyClient.search()
  -> normalized search dto
  -> PluginInvokeResult.output
```

`extract` 调用链：

```text
Runtime / ToolRegistry
  -> plugin.invoke(capability="source.extract", input={url, include_raw_content, ...})
  -> TavilySourcePlugin
  -> TavilyClient.extract()
  -> normalized extract dto
  -> PluginInvokeResult.output
```

## Failure Paths

- 配置缺失
  - 缺少 `api_key_ref` 或注入后 key 为空时，插件返回结构化配置错误。
- capability 不支持
  - `invoke` 收到非 `source.search` / `source.extract` 时返回 `PLUGIN_CAPABILITY_NOT_IMPLEMENTED` 类错误。
- 输入非法
  - `query` 为空、`url` 非法、`max_results` 超限时返回 DTO 校验错误。
- 上游不可用
  - Tavily 超时、限流、响应格式不符合预期时，经 adapter 转为脱敏插件错误。
- 响应字段漂移
  - adapter 负责字段容错和最小归一化；无法归一化时返回结构化错误，不把原始异常直接外泄。

这些失败路径都只停留在“插件调用失败”层，不自动变更 Registry 状态，也不延伸到审计表、DB 或事件链路。

## Validation Plan

OpenSpec 阶段：

- `openspec validate add-tavily-source-tool-plugin --type change --strict --json`

实现阶段最小验证：

- 插件单元测试：`uv run python -m unittest discover -s plugins/sources/tavily-source/tests`
- 必要时补 runtime contract test，证明 manifest entrypoint 可被 runtime 加载并调用

## Open Questions

- `api_key_ref` 最终是否沿用现有 secret reference 命名规范，还是在插件系统里统一替换为更通用字段名？
- Tavily search output 是否需要在第一版就保留 `answer` / `follow_up_questions` 之类扩展字段，还是严格限制为 evidence-oriented 最小集合？
- `extract` 返回 `raw_content` 时，是否需要额外长度限制或截断策略以保护后续 tool payload 体积？
