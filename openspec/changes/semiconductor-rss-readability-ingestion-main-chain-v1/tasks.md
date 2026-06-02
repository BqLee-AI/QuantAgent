## 1. OpenSpec Review Gate

- [ ] 1.1 提交 OpenSpec-only PR，只包含 `semiconductor-rss-readability-ingestion-main-chain-v1` 的 proposal、design、tasks、specs 和必要说明。
- [ ] 1.2 在 PR 说明中链接 issue #260，并明确本 PR 只收住半导体 RSS/Readability 主链路边界，不进入任何实现代码。
- [ ] 1.3 在维护者明确评论“没问题”或批准前，不进入 `plugins/industries/**`、`packages/core/**`、`apps/scheduler/**`、`apps/worker/**` 的实现 PR。

## 2. Industry Package Asset Gate

- [ ] 2.1 后续实现按 `plugins/industries/semiconductor-industry/` 或等价官方目录落半导体行业包资产，至少包含 `plugin.yaml`、`config.schema.json`、README 和 `templates/source_bindings/`。
- [ ] 2.2 固定 RSS baseline required/default-enabled 模板与 RSS expansion optional 模板分层，不把所有源都默认启用。
- [ ] 2.3 固定 Readability 为 optional enrichment source dependency，不让行业包直接发正文抓取 HTTP 请求。

## 3. Worker Enrichment And Topic Gate

- [ ] 3.1 后续实现让 worker 在消费 `source.event.captured` 后，通过受控 enrichment seam 决定是否调用 Readability。
- [ ] 3.2 固定 enrichment 结果至少可表达 `not_needed`、`succeeded`、`failed_degraded` 三类状态，并为 degraded 路径保留结构化失败标记。
- [ ] 3.3 后续实现由 worker 发布 `industry.analysis.requested`，而不是直接把半导体分析实现硬编码进 worker 入口。
- [ ] 3.4 若保留 `IndustryGateway` 过渡 seam，必须让它服务于 topic publish handoff，而不是继续承担 direct business invocation。

## 4. Event Bus And Fact-Layer Alignment

- [ ] 4.1 后续实现同步更新 stable topic policy、事件文档和 contract tests，使 `industry.analysis.requested` 成为正式主链路 topic。
- [ ] 4.2 后续实现保持“RSS capture 先存在、enrichment 后影响 analysis input”的顺序，不让 Readability 成为 source capture existence 的前置条件。
- [ ] 4.3 在实现 PR 证据链中显式说明与 `raw-event-persistence-dedupe-binding-v1` 的协作边界：本 change 复用 capture fact 顺序，不跨界实现 enriched 双层持久化。

## 5. Verification

- [ ] 5.1 运行 `openspec validate semiconductor-rss-readability-ingestion-main-chain-v1 --type change --strict --json`。
- [ ] 5.2 后续实现 PR 至少提供最小 harness，覆盖：半导体 RSS binding 触发、`source.event.captured` 发布、worker enrichment / degraded 路径、`industry.analysis.requested` 发布。
- [ ] 5.3 后续实现 PR 允许使用 fixture / controlled inputs，不要求真实外网 RSS 或真实 article website 作为验收前提。
