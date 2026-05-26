## Why

QuantAgent 已经通过 `#137` 和 `docs/design/11-crawler-source-plugin-boundary.md` 收住了 crawler Source Plugin 的插件包交付边界，也在 `docs/design/06-source-plugin-design.md` 中把 `quantagent.official.source.readability` 列为初版官方 Source Plugin 能力。`#155` 这组 `Readability Link Reader` artifacts 也明确建立在 `#145` 已收敛的 `source-plugin-boundary` 之上，沿用那一层“插件返回标准 DTO、平台接管事件链路”的职责边界。但当前仓库里仍只有 `placeholder-source` 这类最小样例，还没有可复用的正文读取插件。

如果这一层能力继续缺失，后续新闻抓取、公司财报抓取、特定内容搜索等插件 issue 会被迫在同一刀里同时定义 reader 能力、业务抓取逻辑和 fallback 方案，导致 scope 漂移，也会让“插件只负责能力和配置契约，平台负责调度和事件链路”的边界再次变模糊。

这一刀先只收住官方 `Readability Link Reader` Source Plugin 的插件包能力、配置契约和输出 DTO，让后续 crawler / search 类插件能基于统一 reader 能力继续推进。

## What Changes

- 定义官方 `Readability Link Reader` Source Plugin 的插件包边界和最小目录结构。
- 定义 `plugin.yaml`、`config.schema.json`、README、最小测试和入口实现的最小交付物要求。
- 定义插件最小配置契约，覆盖 `url`、可选 `headers`、`timeout_seconds` 和必要的正文抽取参数。
- 定义插件输出贴齐平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO。
- 明确插件只负责链接读取、正文抽取、标准化和清晰失败返回，不负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限和生命周期。
- 允许插件内部封装成熟 Python 开源正文抽取库，但将依赖视为插件实现细节，不上升为核心系统耦合。

## Capabilities

### New Capabilities

- `source-readability-reader`: 官方 `Readability Link Reader` Source Plugin 对普通网页 URL 执行读取和正文抽取，返回符合平台约定的 Source Plugin 输出结构的标准 DTO，供平台写入事件链路。

## Impact

- `plugins/sources/readability-source/`
- `packages/core/tests/test_core.py` 或同级插件契约验证入口
- `docs/design/06-source-plugin-design.md`
- `docs/design/11-crawler-source-plugin-boundary.md`
- 可能新增一个插件内部 Python 依赖，但该依赖只属于插件实现细节，不应改变 core / API / web 的依赖边界
