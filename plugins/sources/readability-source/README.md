# Readability Source

官方的 Readability Link Reader Source Plugin。

## 边界

- 对单个公开网页 URL 执行抓取、正文抽取和标准化。
- 返回 `SourceFetchResult` / `SourceItemDraft` 形状的 source 输出，由平台后续决定如何入库、去重和审计。
- 交付内容只包括插件目录、`plugin.yaml`、`config.schema.json`、README、入口实现和最小测试。
- 只提供 `source.fetch` 能力，不暴露 `tool.read_url`。
- 不负责 Registry 扫描、API 接入、Runtime 无感接入、Scheduler、SourceBinding、RawEvent 入库或 Event Bus 发布。
- 不负责行业路由、分析、通知、执行、浏览器自动化、复杂反爬或代理池。
- 不在插件包内存储 secret、私有 cookie、站点白名单或生产抓取策略。

QuantAgent core 负责发现、校验、配置、绑定、调度、重试、限流、去重、持久化和审计。

## 配置

配置见 `config.schema.json`。默认网页 URL 和可选请求参数由 Runtime 注入到插件配置中；调用方也可以通过 `source.fetch` 的 input 传入本次请求的 URL。
