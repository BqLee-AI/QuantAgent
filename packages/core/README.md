# quantagent-core

`packages/core` 是 QuantAgent 的共享基础设施包。

当前这里包含：

- 插件 Registry / Runtime / Scheduling
- Event Bus（memory / kafka）
- 数据库与配置基础能力
- 一些最小的演示和验证入口

## 演示入口

| Demo | 说明 |
| --- | --- |
| [quantagent-demo CLI](../docs/demo/quantagent-demo-cli.md) | 最小闭环：插件扫描 → 触发 → 事件发布 → 消费 |
| [插件底座 Demo](../docs/demo/plugin-registry-v1-pseudocode.md) | Registry → Runtime → Scheduling 全链路说明 |
