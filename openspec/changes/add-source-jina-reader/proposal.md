## Why

QuantAgent 已经通过 `#137`、PR `#145`、`docs/design/11-crawler-source-plugin-boundary.md` 和 `docs/design/06-source-plugin-design.md` 收住了 crawler / reader 类 Source Plugin 的插件包交付边界，并把 `quantagent.official.source.jina` 列为初版官方 Source Plugin 能力之一。当前 `Readability Link Reader` 已经有独立 issue / OpenSpec / 实现链路作为并行 reader 先例，但仓库里仍没有官方 `Jina Reader` Source Plugin 可供后续 crawler / search 类插件复用。

如果这一层能力继续缺失，后续新闻抓取、财报抓取、搜索类插件仍可能在自己的 issue 里重复定义外部 reader fallback、鉴权边界和敏感链接外发规则，导致 scope 再次漂移，也会让“插件只负责读取与标准化，平台负责权限、调度和审计”的边界重新模糊。

这一刀先只收住官方 `Jina Reader` Source Plugin 的插件包能力、配置契约、外部 reader 使用边界和标准输出 DTO，让后续 crawler / search 类插件能在与 `Readability` 平行的边界上复用第二条 reader 路径。

## What Changes

- 定义官方 `Jina Reader` Source Plugin 的插件包边界和最小目录结构。
- 定义 `plugin.yaml`、`config.schema.json`、README、最小测试和入口实现的最小交付物要求。
- 定义插件最小配置契约，覆盖 `url`、可选非敏感请求参数和超时控制，不在插件公开 schema 中暴露原始外部 reader 鉴权字段。
- 定义插件输出贴齐平台约定的 Source Plugin 输出结构 / source runtime 可消费输出 DTO，不把本 change 绑定到 core 内部 DTO 名称或文件路径。
- 明确插件只负责通过 `Jina Reader` 类服务读取内容、标准化输出和清晰失败返回，不负责 `RawEvent` 入库、去重、`SourceBinding`、Event Bus、权限和生命周期。
- 明确是否允许将 URL 发送给外部 reader 由平台策略边界决定，插件只遵循平台传入的允许/禁止外发结果并返回清晰拒绝或失败信息。

## Capabilities

### New Capabilities

- `source-jina-reader`: 官方 `Jina Reader` Source Plugin 对普通网页 URL 执行外部 reader 读取和文本标准化，返回平台约定的 Source Plugin 输出结构，供平台写入事件链路。

## Impact

- `plugins/sources/jina-source/`
- `docs/design/06-source-plugin-design.md`
- `docs/design/11-crawler-source-plugin-boundary.md`
- 后续实现阶段可能新增 `plugins/sources/jina-source/` 下的插件包与插件内部测试，但不应要求修改 core / API / web 才能成立
