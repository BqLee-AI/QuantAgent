# RSS Source

官方的 RSS 和 Atom 拉取式 Source Plugin。

## 边界

- 从公开 feed 条目生成 `RawEventDraft` 记录。
- 交付内容只包括插件目录、`plugin.yaml`、`config.schema.json`、README、入口实现和最小测试。
- 不自行启动轮询循环。
- 不负责 Registry 扫描、API 接入、Runtime 无感接入、Scheduler、SourceBinding、RawEvent 入库或 Event Bus 发布。
- 不负责行业路由、分析、通知或执行。
- 不在插件包内存储 secret、私有 feed 列表或生产站点配置。

QuantAgent core 负责发现、校验、配置、绑定、调度、重试、限流、去重、持久化和审计。

## 配置

配置见 `config.schema.json`。Feed URL 应放在 `SourceBinding` 的 effective config 中，而不是写进这个插件包。
