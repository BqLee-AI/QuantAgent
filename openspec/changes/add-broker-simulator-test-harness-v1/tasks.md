## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `add-broker-simulator-test-harness-v1` 的 proposal、design、specs、tasks 和必要元数据。
- [x] 1.2 在 PR 说明中写清楚：本 PR 只定义 broker simulator test harness V1，不接真实券商、不实现 live trading、不混入 #152 的具体 plugin 实现。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入代码实现。

## 2. Harness 契约冻结

- [x] 2.1 盘点 `packages/core/src/quantagent/core/wallet/**` 的现有 service-level 受控入口，优先复用 `WalletService` 公开命令与查询方法，确认 execution、ledger、cash、position 和 paper order/paper execution 的最小可测试注入点。
- [x] 2.2 定义第一版 broker-shaped 测试协议或 helper，至少覆盖 account、cash、position、order、execution 和 broker error 输入，并明确这些 shape 首先用于测试上下文与断言，不等于新增 broker snapshot sync API。
- [x] 2.3 为 execution 输入固定账户范围内稳定的 `external id` / `source key` 语义，并明确它映射到当前 core 的 `idempotency_key` 或等价 service seam。
- [x] 2.4 明确 harness 只通过 wallet core service-level 受控入口驱动状态，不允许 repository 直写、ORM 直写或 API route 注入。

## 3. Core 测试资产实现

- [x] 3.1 在 `packages/core/tests/**` 落地 simulator fixture 或 in-memory broker helper，保证无网络、无真实 secret 即可运行。
- [x] 3.2 实现 full fill execution 场景，验证 cash、position、paper execution 和 append-only ledger 在同一入账链路下保持一致。
- [x] 3.3 实现 duplicate execution 幂等场景，验证同一 `source key` 不会重复扣现金、重复加持仓或重复追加 ledger。
- [x] 3.4 实现 reject 或 insufficient cash 场景，验证失败输入不会制造错误入账状态；并明确该场景是 broker-side 负路径验证，不要求本轮新增真实券商式资金预检查能力。
- [x] 3.5 实现 fee 与多币种字段场景，验证金额、手续费、价格、数量和相关货币字段保持 Decimal / 定点语义。

## 4. Contract-Style 测试收口

- [x] 4.1 把关键场景组织为后续真实 paper broker adapter 可复用的 contract-style 测试入口，而不是散落的内部单测；入口职责限定为“接收 broker-shaped fixture 并触发 wallet service 调用”。
- [x] 4.2 测试名称、fixture 名称和说明文案明确使用 `broker simulator` / `paper harness`，不暗示 live broker sync、真实执行或资金操作已完成。
- [x] 4.3 如果当前结构允许，可补一个可选 partial fill 扩展点；若不做，实现说明里要明确它被 defer，而不是被 silently ignored。

## 5. 文档与验证

- [x] 5.1 在相关 README、测试说明或 change 文档中写明 harness 的运行方式、覆盖场景和明确非目标。
- [x] 5.2 运行与变更范围匹配的 Python 测试，证明 harness 在无网络、无真实账户、无真实密钥的环境下可重复通过。
- [x] 5.3 运行 `openspec validate add-broker-simulator-test-harness-v1 --type change --strict --json`。
- [x] 5.4 在实现 PR 说明中写清楚：依据来自 issue #157 与 `portfolio-wallet-core-v1` stable spec；已验证哪些场景；reject / insufficient cash 采用了哪种负路径表达；partial fill、plugin runtime 集成、真实 broker adapter 与 broker snapshot sync 仍未进入本轮。
