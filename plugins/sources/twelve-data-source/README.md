# Twelve Data Quote Source

官方 Twelve Data latest quote 拉取式 Source Plugin。

## 边界

- 按配置的 `symbols` 列表调用 Twelve Data `/v1/quote` 或等价接口拉取最新报价。
- 将每条行情标准化为平台约定的 `RawEventDraft`，`source_type` 固定为 `market_quote`。
- 交付内容只包括插件目录、`plugin.yaml`、`config.schema.json`、README、入口实现和最小测试。
- 不自行启动轮询循环或后台线程。
- 不负责 Registry 扫描、API 接入、Runtime 无感接入、Scheduler、SourceBinding、RawEvent 入库或 Event Bus 发布。
- 不负责行业路由、分析、通知或执行。
- 不在插件包内存储 secret、真实 API key 或生产站点配置。
- 不做 WebSocket / stream source、历史 K 线、技术指标或多 provider 聚合。

QuantAgent core 负责发现、校验、配置、绑定、调度、重试、限流、去重、持久化和审计。

## 配置

配置见 `config.schema.json`。

- `symbols`（必填）：要拉取最新报价的股票代码列表，例如 `["AAPL", "MSFT", "0700.HK"]`。
- `market`（可选）：市场标识，例如 `"NASDAQ"`。
- `timeout_seconds`（可选）：HTTP 请求超时秒数，默认 10。

### API Key

Twelve Data API key 由平台通过 secret 管理注入到 `effective_config` 的 `twelve_data_api_key` 字段中，**不在插件的公开配置中填写**。插件在 `fetch()` 中从 config 读取该字段；若缺失则返回清晰错误。

### 频率约束

Twelve Data 免费 plan（Free Tier / Basic）同时受每分钟和每日额度约束：

- 建议单次 `symbols` 数量控制在 1–5 个以内。
- 建议由平台调度策略将轮询间隔设为 60 秒及以上。
- 超出免费配额时，Twelve Data 可能返回 `429`，插件对此返回清晰失败信息。

## 输出结构

每个 `RawEventDraft` 字段约定：

| 字段 | 值 |
|---|---|
| `source_plugin_id` | `quantagent.official.source.twelve_data` |
| `source_type` | `market_quote` |
| `external_id` | `twelve_data:{symbol}:{quote_timestamp}` |
| `title` | `{symbol} @ {price}` |
| `raw_payload` | 完整的 Twelve Data API 响应 JSON |
| `metadata.provider` | `twelve_data` |
| `metadata.symbol` | 股票代码 |
| `metadata.price` | 最新价格 |
| `metadata.currency` | 货币，如 `USD`、`HKD` |
| `metadata.market` | 市场，如 `NASDAQ`、`HKEX` |
| `metadata.quote_timestamp` | API 返回的报价时间 |

## 测试

最小测试使用 mock / fixture 驱动，不依赖真实 Twelve Data 服务稳定性。