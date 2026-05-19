# Issue 写作原则

## 合格 issue 的定义

合格的 QuantAgent 开发 issue 是一个可接手、可验证、边界清楚的小问题。它通常来自：

- 设计文档和当前实现之间的缺口
- OpenSpec change 拆出的独立任务
- 已实现能力暴露出的契约、验证或体验风险
- 需要先被收口的架构或产品边界

它不是：

- 多个产品能力混在一起的大包
- 只有 “实现 X” 的施工标题
- 没有背景、非目标和验收的占位符

## Discussion 到 Issue 的压缩方式

从讨论、PR 评论或用户粗略需求生成 issue 时，按这个顺序压缩：

1. 先找真正的担心：现在继续模糊会让哪个设计、实现或验证漂移？
2. 再选本轮的一刀：只收一个问题，不把相邻能力一起带进来。
3. 再写非目标：明确哪些能力留给后续 issue 或 change。
4. 再写证据链：链接设计、PR、日志、issue、OpenSpec 或代码位置。
5. 最后写验收：让后续实现和 PR review 能判断是否完成。

不要把讨论原文搬进 issue。issue 应该是讨论被加工后的协作对象。

## Readiness 检查

任一问题答不清时，不要标记 `status:ready`：

1. 为什么现在要做？
2. 这一刀收住的单一问题是什么？
3. 哪些内容明确不做？
4. 哪些上游文档、OpenSpec、issue 或 PR 是输入？
5. 什么结果算成功，什么结果明确不算成功？
6. 哪些点需要维护者确认，不能由实现者自行脑补？

## Package 和边界检查

如果 issue 要新增目录、package 或长期抽象，必须额外说明：

- 现有 `apps/`、`packages/`、`plugins/`、`runtime/` 哪个边界最接近？
- 为什么不能放进已有边界？
- 新 package 的上游和下游依赖是什么？
- 是否会违反 `packages/core` 不依赖 app/plugin 的规则？
- 是否会让 API router、前端页面或插件承担不属于自己的核心逻辑？

没有明确复用需求、跨 app 需求或契约真源时，不要为“以后可能用”创建 package。

## 新技术栈检查

涉及较新的框架、库或 API 时，issue 要提醒实现者不要盲信模型记忆：

- 优先查本仓库已安装版本、lockfile、README 和现有代码。
- 必要时查官方文档或 package release notes。
- AI review 或模型建议可能基于旧版本 API；需要用当前版本验证。
- 如果采用新依赖，说明为什么现有栈不能满足，以及最小验证命令。

## QuantAgent 常见非目标

按 issue 主题选择，不要机械全写：

- 不接入真实交易执行、真实券商、真实密钥或生产账户。
- 不把 dry-run 或通知能力升级成 live trading。
- 不绕过 Decision / Policy Gate 或人工审批。
- 不在 API router 中承载核心领域逻辑。
- 不让插件提供自定义前端组件。
- 不把 runtime 本地数据、插件安装产物或 secrets 提交进仓库。
- 不生成静态 OpenAPI、前端 client 或契约代码，除非 issue 明确要求。
- 不引入重型 E2E，除非交互风险已经超过单元或契约测试能覆盖的范围。

## Harness 选择

验证跟风险走：

- OpenSpec：`openspec validate <change-id> --type change --strict --json`
- API route / envelope / OpenAPI：`cd apps/api && uv run python -m unittest discover -s src/tests`
- Web 纯逻辑：`bun run --cwd apps/web test:unit`
- Web 路由、页面、浏览器 API：`bun run --cwd apps/web test:e2e`
- Web 组件浏览器行为：`bun run --cwd apps/web test:ct`
- 前端静态检查：`bun run lint`、`bun run build`、`bun run fmt:check`

不要把外部网络、真实 PostgreSQL 之外的生产依赖、真实凭证或 live trading 写成默认验收条件。
