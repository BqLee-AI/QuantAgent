# RSS Source

这是一个官方 `source` 插件包，插件 ID 为 `quantagent.official.source.rss`。

它只负责：

- 拉取 RSS / Atom feed
- 解析 feed entry
- 标准化输出 `plugin-sdk` 里的 `SourceFetchResult`

它不负责：

- `RawEvent` 入库
- 去重
- `SourceBinding`
- `Event Bus`
- 调度生命周期
- 全文抓取编排

也就是说，RSS 插件不负责 `RawEvent` 入库、不负责 dedupe、不负责 `Event Bus`、不负责调度生命周期。

这意味着它只是一个最小官方 RSS source 插件包，不是完整 source ingestion 主链路，也不代表平台已经具备正式 RSS 闭环。

## 插件职责

- 只实现 `source.fetch`
- 只消费平台传入的校验后配置 / `effective_config`
- 只返回 `SourceFetchResult` + `SourceItemDraft`

之所以只做 `source.fetch`，是因为当前 source 插件契约已经收口到 `source.fetch -> SourceFetchResult`，平台后续是否调度、是否发布事件、是否入库都属于插件外部职责。

## 最小配置

```json
{
  "feeds": [
    "https://example.com/feed.xml"
  ],
  "timeout_seconds": 10,
  "headers": {
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8"
  },
  "user_agent": "QuantAgentRSSSource/0.1",
  "max_items_per_feed": 20,
  "max_response_bytes": 262144,
  "max_content_chars": 4000,
  "keywords": [
    "hbm",
    "memory"
  ],
  "include_content": true
}
```

字段说明：

- `feeds`
  必填，RSS / Atom feed URL 列表
- `timeout_seconds`
  单次 HTTP 请求超时
- `headers`
  可选请求头
- `user_agent`
  默认 `User-Agent`
- `max_items_per_feed`
  每个 feed 最多输出多少条 entry
- `max_response_bytes`
  单个 feed 响应体大小上限，避免异常 feed 撑大内存和输出
- `max_content_chars`
  单条内容片段最大长度，超出后会截断
- `keywords`
  可选关键词过滤，命中 title / content / url 任一字段时保留该 entry
- `include_content`
  是否输出 feed 层 summary / content snippet

约束说明：

- `feeds` 当前最多 20 条，避免一次调用触发无上限外部请求
- `keywords` 是轻量包含匹配，不是语义检索，也不会调用模型做分类
- `headers` 只允许非敏感公共请求头；`Authorization`、`Cookie`、`X-Api-Key` 这类敏感头不允许明文放在插件配置里

## 输出结构

每条 `SourceItemDraft` 至少会带这些字段：

- `external_id`
- `url`
- `title`
- `content`
- `author`
- `published_at`
- `captured_at`
- `raw_payload`
- `metadata`

`metadata` 至少包含：

- `plugin_id`
- `feed_url`
- `feed_title`
- `entry_id`
- `content_type`

实现上只保证 `content` 来自 feed 自带的 `summary` / `description` / `content` 片段，不保证正文完整，更不会在插件内部自动继续抓全文。
同时会对单个 feed 响应体和单条 `content` 长度做上限控制，避免异常 RSS 把插件输出放大成超大 payload。

## 与 `readability-source` 的关系

`rss-source` 和 `readability-source` 是平台层协作关系，不是内嵌关系。

- `rss-source` 负责发现和标准化 feed entry
- `readability-source` 负责读取单个网页 URL 的可读正文

如果某条 RSS entry 后续需要抓取全文，应由平台编排在插件外决定是否继续调用 `readability-source`，而不是把 `readability-source` 硬编码嵌进 RSS 插件内部。

## 非目标

本插件明确不做：

- 调度循环
- `RawEvent` / `Event` 入库
- 去重
- Event Bus 发布
- Router / industry analysis / approval
- worker / scheduler 入口改造
- API 改造
- 全文 reader fallback 编排

## 当前格式支持

- 支持 Atom
- 支持常见 RSS 2.0
- 当前不支持 RSS 1.0 / RDF；遇到 RDF feed 会返回明确错误，而不是静默给空结果

## 本地验证方式

在仓库根目录执行：

```bash
uv run python -m unittest discover -s plugins/sources/rss-source/tests -v
```

测试策略：

- 使用静态 RSS / Atom XML fixture
- 使用受控假响应，不依赖真实外网
- 验证输出可被 `SourceFetchResult.from_mapping(...)` 重建
