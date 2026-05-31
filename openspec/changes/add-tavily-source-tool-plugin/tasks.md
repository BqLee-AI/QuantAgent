## 1. Boundary Gate

- [ ] 1.1 固定 Tavily 第一版 capability 只包含 `search` / `extract`，不引入 `crawl`、`map`、`research` 或插件编排能力。
- [ ] 1.2 固定 Tavily 作为 evidence source/data tool 的职责边界：只提供受控工具能力，不承担 Runtime、ToolRegistry、事件链路、审计或调度。
- [ ] 1.3 固定 Tavily 不直接 import 或调用 RSS、Readability、Discord、Binance 或其他插件实现。

## 2. Runtime Contract Gate

- [ ] 2.1 在设计与实现说明中固定“协议优先、可选继承 `BasePlugin`”的接入策略。
- [ ] 2.2 固定插件 entrypoint 必须满足 `RuntimePlugin` 协议，并继续通过 `plugin.yaml` + manifest entrypoint 接入 runtime。
- [ ] 2.3 固定插件只消费 runtime 注入的只读 config / metadata，不自行发现 secret、DB 或内部 service。

## 3. Package Blueprint Gate

- [ ] 3.1 固定 `plugins/sources/tavily-source/` 的最小交付物：`plugin.yaml`、`config.schema.json`、README、`src/` 入口与 adapter、`tests/` 和 fixture。
- [ ] 3.2 固定 `src/tavily_source.py` 负责 capability 分发、输入校验和输出组装。
- [ ] 3.3 固定 `src/tavily_client.py` 负责 Tavily 第三方请求、错误包装和字段归一化，不把第三方协议细节散落到入口文件。

## 4. Schema And DTO Gate

- [ ] 4.1 定义 `search` 工具 ID、输入字段和输出字段草案，确保结果 JSON-safe、可校验、可序列化。
- [ ] 4.2 定义 `extract` 工具 ID、输入字段和输出字段草案，确保结果 JSON-safe、可校验、可序列化。
- [ ] 4.3 使 Tavily 输出对齐 `SourceFetchResult`，并通过 metadata 保留 search/extract 的 evidence 语义。
- [ ] 4.4 固定最小配置字段草案：`api_key_ref`、`timeout_seconds`、`default_max_results` 和必要的 extract/search 参数。

## 5. Verification Gate

- [ ] 5.1 约定测试必须使用 fake client 或静态 fixture，不依赖真实 Tavily API key 或外部网络。
- [ ] 5.2 覆盖 `search` / `extract` 成功、配置缺失、capability 不支持、上游失败和 DTO 校验失败。
- [ ] 5.3 运行 `openspec validate add-tavily-source-tool-plugin --type change --strict --json`。
- [ ] 5.4 基于本 change 创建 OpenSpec-only PR，等待维护者明确评论“没问题”或批准后再进入实现。
