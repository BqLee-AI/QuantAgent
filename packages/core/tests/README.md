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

## Alpaca paper adapter spike

`alpaca_paper_adapter_spike.py` 把 Alpaca paper 接入限制在测试 / spike 边界，只复用 #157 已冻结的 contract 资产：

- `BrokerSimulatorHarness`
- `BrokerSimulatorFixture`
- `BrokerSimulatorOrderInput`
- `BrokerSimulatorExecutionInput.source_key`
- `BrokerSimulatorErrorInput`
- `WalletService.ingest_paper_execution()`

配置约定：

- `ALPACA_PAPER_BASE_URL` 默认且唯一允许值：`https://paper-api.alpaca.markets`
- `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY`：只从环境变量读取
- `QUANTAGENT_ALPACA_PAPER_SMOKE=1`：启用只读外部 smoke
- `QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE=1`：在只读 smoke 基础上额外启用下单 smoke
- 默认超时：`10s`
- 默认下单白名单：`AAPL`、`MSFT`、`SPY`
- 下单上限：`notional <= 5 USD` 或 `quantity <= 1`

当前映射结论：

- Alpaca `cash` 映射为 broker-shaped cash context，可作为 harness 初始资金输入
- Alpaca `buying_power` 只记录为 broker account context，不作为 wallet cash ledger 真源
- Alpaca `positions` 映射到 `BrokerSimulatorPositionContext`
- Alpaca `orders` 映射到 `BrokerSimulatorOrderInput`，仅表达 broker order state，不替代 execution fact
- Alpaca `account activities / FILL` 映射到 `BrokerSimulatorExecutionInput`
- execution `source_key` 使用账户范围稳定键：`<account_id>:alpaca:activity:<activity_id>`
- 重放同一 `activity_id` 仍经由 wallet core 幂等路径，不直接写 wallet 表

验证方式：

```bash
uv run --package quantagent-core python -m unittest discover -s packages/core/tests -p 'test_alpaca_paper_adapter_*.py'
```

只读外部 smoke 默认 skip，不需要网络、credentials 或 `.env`。显式启用后，它只读取 account、positions 和 orders，不写入 wallet state。

```bash
QUANTAGENT_ALPACA_PAPER_SMOKE=1 \
APCA_API_KEY_ID=redacted \
APCA_API_SECRET_KEY=redacted \
uv run --package quantagent-core python -m unittest discover -s packages/core/tests -p 'test_alpaca_paper_adapter_smoke.py'
```

可选下单 smoke 只有在额外开启 `QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE=1` 时才会提交一笔受上限约束的 paper order。它只断言提交与查询状态，不要求真实成交。
