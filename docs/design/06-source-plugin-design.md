# 06. Source Plugin 设计

## 文档状态

**状态**：草案 v0.2  
**范围**：数据源插件接口、采集模式、统一调度器、统一事件输出、配置归属、去重、限流、原文读取、Event Bus 边界  
**当前约定**：Source Plugin 是固定插件类型之一，通过 `plugin.yaml` 注册；Source Plugin 可暴露工具，但必须统一进入 ToolRegistry  
**不包含**：Playwright crawler、复杂反爬、代理池、原始网页快照存储系统

## 设计原则

- Source Plugin 只负责采集、接收、标准化原始信息，不直接做行业判断。
- Source Plugin 产出的事件必须先进入 Event Bus，再由 Router Agent 和 Industry Plugin 处理。
- Source Plugin 可以暴露查询类工具，但工具必须注册到 ToolRegistry，并接受权限、限流和审计管理。
- 不同 source 的输出必须归一到统一 RawEvent / Event 输入结构。
- 插件开发者只声明插件能力和配置 schema；配置校验、保存、启停、调度和审计由平台负责。
- 配置支持“插件默认配置 + 行业包引用覆盖”，方便不同行业包复用同一个 source 插件。
- Pull 类 Source Plugin 不允许自己随意启动轮询循环，必须由统一 Scheduler 管理调度。
- 需要读取链接原文时，初版只通过 Readability Link Reader 和 Jina Link Reader 两类插件/工具实现。
- Playwright crawler 不进入初版，作为后续版本能力。

## Source Plugin 定位

Source Plugin 有两种能力：

```text
Source Plugin
  -> produces RawEvent
  -> exposes optional tools
```

### 产出事件

Source Plugin 通过拉取、接收或订阅外部信息，产出 `RawEvent`，再由核心系统标准化为 `Event`。

插件只负责产出平台约定的 source 输出结构；进入核心系统后的 `RawEvent` 入库与事件链路由平台负责。插件不负责：

- `RawEvent` 入库
- 去重
- `SourceBinding`
- Event Bus 发布
- 权限控制
- 生命周期托管

### 暴露工具

Source Plugin 可以暴露工具，例如：

- RSS 搜索。
- X API 用户时间线查询。
- Readability 链接正文读取。
- Jina 链接正文读取。

这些工具不能被插件直接注入 Agent，必须统一进入 ToolRegistry。

## Source 类型

Source Plugin 分为三类：

```text
pull    -> 主动轮询，例如 RSS、URL watcher
push    -> 外部回调，例如 webhook
stream  -> 长连接订阅，例如 X stream、行情流
```

初版只实现 `pull`，但接口和 manifest 保留 `push`、`stream`。

Source Plugin 在 `plugin.yaml` 中声明执行模式：

```yaml
execution_mode: pull
```

这样可以让 Scheduler、worker、Event Bus 根据 execution mode 做不同调度。

## 统一调度器

Pull 类数据源由统一 Scheduler 管理。插件不能自己写 while loop 或后台线程。

### Scheduler 职责

- 读取 SourceBinding 和 effective config。
- 计算下一次抓取时间。
- 控制抓取频率。
- 控制并发。
- 应用限流、重试、超时和熔断策略。
- 记录每次调度结果。
- 支持暂停、恢复和手动触发。
- 将 fetch 结果写入 RawEvent，再进入 Event Bus。

### 调度对象

调度器调度的不是裸 Source Plugin，而是 SourceBinding。

```text
SourceBinding
  id
  source_plugin_id
  owner_type
  owner_id
  effective_config
  schedule_policy
  retry_policy
  rate_limit_policy
  status
```

原因：

- 同一个 RSS source 插件可能被石油行业包和半导体行业包同时引用。
- 两个行业包的关键词、频率、账号列表可能不同。
- 调度应该以“某个行业包对某个 source 的引用”为单位，而不是只以 source 插件为单位。

### Scheduler 运行位置

初版可以在 `apps/worker` 内运行 scheduler loop，但代码上保留独立 `apps/scheduler` 的边界。

后续如果任务量变大，可以把 scheduler 拆成独立容器。

## 统一事件输出

Source 输出采用 RawEvent -> Event 双层结构：

```text
Source Plugin -> RawEvent -> Normalizer -> Event
```

### RawEvent

```text
RawEvent
  id
  source_plugin_id
  source_type
  external_id
  url
  title
  content
  author
  published_at
  captured_at
  raw_payload
  metadata
```

### Event

Event 是系统主流程使用的标准化事件。Router Agent、Industry Plugin、Decision 和 UI 都只依赖 Event，不直接依赖某个 source 的私有格式。

## 配置归属

Source 配置采用“Source 默认配置 + 行业包引用覆盖”。

```text
source default config
  + industry source binding override
  = effective source config
```

插件开发者只声明自己需要的配置字段，例如：

- `url`
- `frequency`
- `headers`
- `filters`
- `keywords`
- `symbols`
- `accounts`
- `time_window`

用户通过控制台或 API 填写配置；平台负责 schema 校验、保存和绑定，并将校验后的 DTO / `effective_config` 传给插件。

### Source 默认配置

由 Source Plugin 提供，描述插件的默认行为，例如默认超时、默认请求头、默认抓取间隔上限。

### 行业包覆盖配置

由 Industry Package 在引用 Source Plugin 时提供，例如：

- 关键词。
- 账号列表。
- RSS feed 列表。
- 抓取频率。
- 过滤规则。

### 设计原因

- Source 插件可独立运行。
- 行业包可以覆盖关键词、账号、频率、过滤规则。
- 支持同一个 Source Plugin 被多个行业包复用。
- 统一 Scheduler 可以按 SourceBinding 的 effective config 执行调度。
- 平台统一负责配置真相、调度和运行时编排，避免插件自行扩展为小型 runtime。

## 去重策略

去重采用组合 dedupe key。

```text
source_plugin_id
external_id
canonical_url
content_hash
published_at
```

初版规则：

- 优先使用 `source_plugin_id + external_id`。
- 如果没有 external id，使用 `canonical_url + content_hash`。
- 如果内容短或 URL 不稳定，允许 source 插件提供额外 dedupe hint。

## 原文读取插件

初版不做 Playwright crawler。对于需要读取链接原文的场景，提供两个轻量插件/工具。

### Readability Link Reader

用途：

- 对普通网页 URL 执行请求。
- 使用 Readability 类算法抽取正文。
- 返回标题、正文摘要、正文文本、站点信息和 canonical URL。

适用：

- 普通新闻页面。
- 博客文章。
- 文档页面。

限制：

- 不处理复杂动态渲染。
- 不处理强反爬页面。
- 不保存完整网页快照。

### Jina Link Reader

用途：

- 通过 Jina Reader 类服务读取 URL 内容。
- 将网页转为更适合 LLM 消费的文本。
- 作为 Readability 失败或效果不佳时的备选。

适用：

- 需要更稳定正文抽取的网页。
- 需要快速将 URL 转为 Markdown / text 的场景。

限制：

- 依赖外部服务可用性。
- 需要限流、超时和失败降级。
- 敏感或私有链接不应默认走外部 reader。

### ToolRegistry 集成

两个 reader 都以 Source Plugin 暴露工具：

```text
quantagent.official.source.readability.read_url
quantagent.official.source.jina.read_url
```

工具必须声明：

- input schema。
- output schema。
- timeout。
- rate limit。
- risk level。
- 是否允许外部请求。

对于新闻、财报、搜索等 crawler 类插件，默认考虑 `Readability` 和 `Jina Reader` 两类读取路径作为兜底或降级方案；是否以内置策略还是复用官方 reader 插件，应在具体 issue / change 中明确。

## Runtime Policy

反爬、限流、代理、失败重试采用统一 runtime policy + 插件扩展 hook。

```text
RateLimitPolicy
RetryPolicy
TimeoutPolicy
CircuitBreakerPolicy
ProxyPolicy
```

规则：

- Source Plugin 不能绕过全局限流。
- Source Plugin 可以提供特殊 header、selector、normalizer 等扩展 hook。
- 所有外部请求必须记录来源、耗时、状态和错误摘要。
- 失败重试由 runtime policy 控制，不由插件随意无限重试。

## 原始内容存储

RawEvent 保存必要原始字段，大型内容和完整网页快照暂缓。

初版保存：

- 标题。
- 正文摘要或可控长度正文。
- URL。
- 来源 ID。
- 发布时间。
- 作者。
- raw payload JSON。

暂不保存：

- 完整网页截图。
- 大型 HTML 快照。
- 大文件附件。
- Playwright 浏览器执行产物。

## Event Bus 边界

Source Plugin 不能直接调用行业包。

流程：

```text
Source Plugin
  -> RawEvent
  -> Normalizer
  -> Event Bus
  -> Router Agent
  -> Industry Plugin
```

Source Plugin 可以附带 routing hint，但最终路由由 Router Agent / runtime 决定。

```text
routing_hint:
  industries:
    - oil
  confidence: 0.6
  reason: "source bound to oil package"
```

## Source Plugin 接口

### 基础接口

```text
load(context)
start()
stop()
reload(config)
health_check()
```

### Pull Source

```text
fetch(cursor, config) -> list[RawEvent]
```

### Push Source

```text
receive(payload, headers) -> RawEvent
```

### Stream Source

```text
subscribe(config) -> stream[RawEvent]
```

### Optional Tool Provider

```text
list_tools() -> list[ToolDefinition]
```

## Source Manifest 扩展

```yaml
id: quantagent.official.source.rss
name: RSS Source
type: source
version: 0.1.0
entrypoint: rss_plugin:plugin
execution_mode: pull
capabilities:
  - source.fetch
  - tool.search
config_schema: config.schema.json
```

## 初版官方 Source Plugin

```text
quantagent.official.source.rss
quantagent.official.source.url_watcher
quantagent.official.source.readability
quantagent.official.source.jina
```

说明：

- `rss` 负责 RSS feed 轮询。
- `url_watcher` 负责固定 URL 变化检测。
- `readability` 负责普通网页正文抽取。
- `jina` 负责通过 Jina Reader 类能力读取链接正文。

## 初版实现范围

必须实现：

- `pull` source 协议。
- 统一 Scheduler 基础能力。
- SourceBinding 模型。
- RawEvent 输出结构。
- RawEvent -> Event 标准化流程。
- 组合去重策略。
- 默认配置 + 行业包覆盖配置。
- Runtime policy 基础抽象。
- Source Plugin 通过 Event Bus 发布事件。
- Source Plugin 工具注册到 ToolRegistry。
- Readability Link Reader 插件。
- Jina Link Reader 插件。

暂缓实现：

- `push` source。
- `stream` source。
- Playwright crawler。
- 完整网页快照存储。
- 高级反爬和代理池。

## 待确认问题

暂无。用户已确认采用本文档推荐方案，Playwright crawler 后续版本再考虑。
