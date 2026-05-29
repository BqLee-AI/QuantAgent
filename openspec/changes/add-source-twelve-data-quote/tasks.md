## 1. Plugin Contract Gate

- [ ] 1.1 固定 `Twelve Data` 插件包边界：只做 latest quote `pull source`，不做历史数据、新闻联动或 WebSocket 行情流。
- [ ] 1.2 固定插件输出贴齐平台约定的 Source Plugin 输出结构，不新增平台级 quote 专用 DTO，也不在本 change 中绑定 core 内部 DTO 名称。
- [ ] 1.3 固定 `source_type` 首版使用 `market_quote`，并明确 `external_id` 采用 `provider:symbol:quote_timestamp` 约定。
- [ ] 1.4 固定插件不负责调度、`RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限和生命周期。

## 2. Provider Boundary Gate

- [ ] 2.1 固定插件公开最小配置字段集合：`symbols`、可选 `market`、可选 `timeout_seconds` 和必要的最小非敏感控制字段。
- [ ] 2.2 记录 Twelve Data API key 等敏感鉴权信息由平台统一控制，不把真实密钥作为插件公开 schema 普通字段提交到仓库。
- [ ] 2.3 明确首版按分钟级 pull source 设计，频率和 credits 约束由平台 scheduler / binding policy 控制，插件不自行轮询。
- [ ] 2.4 明确 Twelve Data 限流、超时、服务不可用或响应异常时，本轮只要求清晰失败返回，不引入 provider fallback。

## 3. Verification Gate

- [ ] 3.1 约定最小交付物：`plugin.yaml`、`config.schema.json`、README、入口实现、最小测试。
- [ ] 3.2 约定最小验证优先使用 mock / fixture / 受控响应，不依赖真实 Twelve Data 服务稳定性。
- [ ] 3.3 运行 `openspec validate add-source-twelve-data-quote --type change --strict --json`。
- [ ] 3.4 基于本 change 创建 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入实现。
