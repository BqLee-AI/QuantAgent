## 1. OpenSpec 评审

- [ ] 1.1 创建 OpenSpec-only issue，跟踪 `official-plugin-v1-main-chain` 的评审、阻塞和后续拆分。
- [ ] 1.2 提交 OpenSpec-only PR，只包含本 change 的 proposal、design、specs、tasks 和必要元数据。
- [ ] 1.3 在 PR 说明中写清楚：本 PR 只定义官方插件 V1 主链路，不实现插件代码、不改 runtime、不接真实交易。
- [ ] 1.4 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再推进具体插件实现 issue。

## 2. 具体插件 issue 拆分

- [ ] 2.1 新开 RSS Source Plugin V1 issue，明确不沿用旧的 RawEvent 入库大范围。
- [ ] 2.2 新开 Tavily Source/Data Tool Plugin V1 issue，第一版只做 `search` / `extract`。
- [ ] 2.3 新开 Analysis Plugin V1 issue，收住 AnalysisResult DTO。
- [ ] 2.4 新开 Strategy Draft Plugin V1 issue，收住 StrategyDraft DTO 和 Approval 交接。
- [ ] 2.5 新开 Binance Dry-run Executor Plugin V1 issue，明确 dry-run/mock-only。

## 3. 既有 issue 对齐

- [ ] 3.1 将 #139 Readability Link Reader 纳入 official plugin V1 evidence tools。
- [ ] 3.2 将 #110 Discord 插件组收窄为 notification plugin 边界。
- [ ] 3.3 将 #131 审批工作台定义为核心 Approval / Decision 边界，不作为普通插件。
- [ ] 3.4 将 #117 插件管理台定位为后续只读/轻管理入口，不接插件自定义前端。
- [ ] 3.5 明确 #140、#141、#142 是核心底座依赖，不交给具体插件开发者实现。

## 4. 后续实现前置

- [ ] 4.1 DTO 命名和字段与 #142 Plugin IO DTO 对齐。
- [ ] 4.2 Runtime 调用和配置注入与 #140 对齐。
- [ ] 4.3 Pull source 调度与 #141 对齐。
- [ ] 4.4 Approval、Audit、Policy Gate 和 Binance dry-run 的高风险边界需要单独评审后实现。
