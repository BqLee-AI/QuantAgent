# 实现 PR 说明草稿

## 依据

- change `add-alpaca-wallet-api-e2e-validation`
- `openspec/changes/spike-alpaca-paper-adapter/**`
- `openspec/changes/add-broker-simulator-test-harness-v1/**`
- `openspec/changes/add-portfolio-wallet-api-v1/**`

## 前置依赖状态

- 已复用既有 `/api/v1/wallet/**` 只读 routes、DTO 与 envelope；未新增 Alpaca API route。
- 已复用 `packages/core/tests/alpaca_paper_adapter_spike.py` 的 paper-only URL guard、credentials 读取、Alpaca-shaped mapper 与 read-only snapshot 获取逻辑。
- 已复用 `WalletService.ingest_paper_execution()` 的受控入账路径；未新增 runtime adapter、plugin 或 live endpoint。

## 改动摘要

- 新增 `apps/api/src/tests/test_alpaca_wallet_api_e2e.py`：
  - 默认离线 E2E：使用脱敏 Alpaca-shaped account / order / fill fixture，先 seed 本地 wallet state，再通过既有 `/api/v1/wallet/**` route 读回 account、cash、position、ledger、paper order、paper execution。
  - 可选外部 smoke：仅在 `QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE=1`、`QUANTAGENT_ALPACA_PAPER_SMOKE=1`、paper credentials 与 paper URL guard 同时满足时运行。
  - 外部 smoke 只读取 Alpaca paper account、positions、orders；本地 wallet 使用 `acct_alpaca_e2e_redacted`、`order_redacted_*`、`client_redacted_*`、`activity_redacted_*` 等脱敏 identifier，不提交 paper order。
- 更新 `apps/api/README.md`：
  - 记录离线 E2E 的定位、外部 smoke gate、窄验证命令和显式外部 smoke 命令。

## 验证结果

### V0 OpenSpec 严格校验

```bash
openspec validate add-alpaca-wallet-api-e2e-validation --type change --strict --json
```

结果：`valid: true`，`issues: []`。

### V1 现有 API 回归

```bash
uv run python -m unittest apps/api/src/tests/test_app.py
```

结果：`Ran 74 tests ... OK`。

### V2 新增离线 E2E

```bash
uv run python -m unittest apps/api/src/tests/test_alpaca_wallet_api_e2e.py
```

结果：`Ran 2 tests ... OK (skipped=1)`。  
说明：默认只运行离线 E2E；外部 smoke 在未开启 `QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE` 时保持 skip。

### V3 外部 Alpaca paper E2E smoke

实际执行命令：

```bash
QUANTAGENT_ALPACA_WALLET_API_E2E_SMOKE=1 \
uv run python -m unittest apps/api/src/tests/test_alpaca_wallet_api_e2e.py
```

运行时环境已满足：

- `QUANTAGENT_ALPACA_PAPER_SMOKE=1`
- `ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets`
- paper credentials 已通过环境变量注入

结果：`Ran 2 tests ... OK`。  
说明：

- 已实际访问 Alpaca paper
- 未提交 paper order
- 真实读取仅覆盖 account、positions、orders
- 本地 wallet 读回断言只使用脱敏后的 account/order/client order/activity identifiers

### V4 敏感信息验证

- 使用 `rg` 检查新增测试与说明文件，确认仓库内只保留环境变量名与 `redacted` 占位值。
- 未提交真实 API key、secret、真实 account id、order id、client order id 或完整第三方原始响应。

## 结论

- 离线 E2E 已证明：Alpaca-shaped 数据经 `WalletService` 受控入账后，可由既有 `apps/api` wallet routes 稳定读出。
- 外部 Alpaca paper smoke 只作为补充验证，证明当前 paper credentials 与 endpoint 可读，且真实响应可转换为脱敏本地 wallet 输入。
- 当前实现未发现需要放宽 wallet API V1、wallet core V1 或 Alpaca spike contract 的字段映射缺口。

## 非目标重申

- live trading
- 官方 Alpaca plugin
- runtime adapter promotion
- broker reconciliation / snapshot sync
- 真实下单、撤单、改单
