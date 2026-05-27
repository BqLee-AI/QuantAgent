## 背景

issue #157 需要在 `portfolio-wallet-core-v1` 与 `add-portfolio-wallet-api-v1` 之后，补上一层“外部券商形态”的本地可重复验证地基。当前 wallet core 和 API 已经有内部 service、repository 和 route 级测试，但这些测试仍主要从系统内部构造状态，尚不能证明 wallet core 能稳定承接来自外部 adapter 或 plugin 形态的数据输入。

如果现在直接接真实券商 paper / sandbox，会过早引入真实 secret、网络稳定性、登录网关、字段差异和账户安全边界，反而不利于先验证 wallet core 的幂等入账、账本一致性、Decimal 语义和 paper-only 约束。本 change 先定义 broker simulator test harness V1，用受控 fixture 或 in-memory simulator 模拟外部券商输入，让后续真实 paper broker adapter 能复用同一套 contract-style 测试语义。

## 改动

- 新增 `broker-simulator-test-harness-v1` 能力，定义 wallet core 的外部接入式测试边界。
- 规定第一版 harness 以 `packages/core` 测试资产为主，主要通过 `WalletService` 的公开命令与查询边界验证 wallet core，不把 simulator 或 adapter 写入 FastAPI route。
- 定义最小 broker-shaped 测试协议，覆盖外部账户、现金、持仓、paper order、paper execution 与 broker error 场景；其中账户、现金、持仓形状首先作为测试 fixture 与断言上下文，不引申为本轮要新增 broker snapshot sync 持久化能力。
- 规定外部 execution 必须携带账户范围内稳定的 `external id` 或 `source key`，并通过 wallet core 受控入口证明重复提交不会重复入账。
- 规定第一版必须覆盖 full fill、duplicate execution、broker-side rejected 或 insufficient cash、fee、多币种字段和 Decimal 精度；其中 rejected / insufficient cash 的第一版验收是“错误输入不会变成成功入账”，不要求 wallet core 在本轮承担真实券商风控或余额预检查职责。partial fill 只作为可选扩展，不是本轮必收。
- 规定 harness 不连接真实券商 API、不读取真实密钥、不做真实下单或 live trading，不替代 issue #152 的具体 executor plugin 方向。
- 规定 simulator 可以保持 adapter / plugin-shaped 输入边界，但第一版不强制落到 `runtime/plugins`、官方 plugin 目录或 `packages/plugin-sdk` 的稳定 SDK。

## 能力

### 新增能力

- `broker-simulator-test-harness-v1`: 定义 Portfolio Wallet Core V1 的 broker-shaped 本地模拟接入测试边界、幂等执行输入和 contract-style 验证口径。

## 影响

- `packages/core/src/quantagent/core/wallet/**`: 作为 harness 调用的 service-level 受控领域入口和幂等入账真源。
- `packages/core/tests/**`: 第一版 simulator fixture、adapter-shaped contract tests 和 README/说明的主要落位。
- `openspec/specs/portfolio-wallet-core-v1/spec.md`: 本 change 依赖该 stable spec，但不改写其 paper-only core requirement。
- `docs/design/03-plugin-system-and-registry.md`: 作为 plugin-shaped 边界参考；本轮不要求实现 Registry 扫描、`plugin.yaml` 安装或 SDK 生命周期。
- `docs/design/08-api-and-websocket-design.md`: 继续约束高风险动作必须经过 Policy Gate；本 harness 不打开真实执行或 REST 写入入口。
