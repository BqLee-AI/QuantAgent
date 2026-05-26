# packages/core tests

## Broker simulator / paper harness

`wallet_broker_simulator_harness.py` 定义了第一版 broker-shaped 测试协议与 in-memory harness，用来验证 `portfolio-wallet-core-v1` 的受控入账链路，而不是新增生产态 broker snapshot sync API。

当前 shape 覆盖：

- account：测试账户上下文
- cash balance：初始资金上下文
- position context：断言上下文，不是生产持仓导入接口
- order：broker order 视角的 paper order 输入
- execution：broker execution 输入，`source_key` 逐字映射到 wallet core 的 `idempotency_key`
- broker error：broker-side reject / no-op 错误输入

已覆盖场景：

- full fill execution 入账一致性
- duplicate execution 幂等
- broker reject no-op
- insufficient cash 失败不留下部分状态
- fee 与多币种字段
- Decimal / 定点语义

明确非目标：

- 不连接真实券商 API
- 不读取真实密钥、真实账户或网络配置
- 不实现 live trading、broker snapshot sync、reconciliation 或 plugin runtime 集成
- partial fill 在 V1 明确 defer，只保留显式扩展点

运行方式：

```bash
uv run --package quantagent-core python -m unittest discover -s packages/core/tests -p 'test_wallet_broker_simulator_harness.py'
```
