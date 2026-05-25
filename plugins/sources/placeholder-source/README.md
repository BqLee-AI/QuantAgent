# Placeholder Source

官方的占位 Source Plugin，用于演示最小插件包交付结构。

## 边界

- 只提供最小的 `load` / `start` / `stop` / `fetch` 协议占位实现。
- 用来说明官方 Source Plugin 至少应交付 `plugin.yaml`、`config.schema.json`、README 和入口代码。
- 不负责 Registry 扫描、API 接入、Runtime 无感接入、Scheduler、SourceBinding、RawEvent 入库或 Event Bus 发布。
- 不内置真实站点配置、私有抓取规则、token 或 cookie。

QuantAgent core 负责发现、校验、绑定、调度、持久化和审计；插件开发者只负责插件包本身能力与目录交付。
