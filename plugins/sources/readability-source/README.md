# Readability Link Reader

`Readability Link Reader` 是官方 `source` 插件，负责读取单个网页 URL 并提取可读正文。

## 能力边界

- 只提供 `source.fetch` 能力，不暴露 `tool.read_url`。
- 只消费平台传入的校验后配置 / `effective_config`。
- 返回平台约定的 Source Plugin 输出结构。
- 不负责 `RawEvent` 入库、去重、`SourceBinding`、`Event Bus`、权限或生命周期。

## 最小配置

- `url`
- 可选 `headers`
- 可选 `timeout_seconds`
- 可选 `min_text_length`

## 依赖策略

- 当前实现优先使用 Python 标准库完成 HTTP 请求和 HTML 正文抽取，避免把 reader 插件和 core / API / web 的依赖边界绑死。
- 如果后续站点兼容性需要增强，允许只在本插件内部封装成熟 Python 开源正文抽取库；这类依赖仍属于插件实现细节，不上升为 core / API / web 的共享依赖。

## 验证

- 最小测试使用静态 HTML fixture 和受控假响应，不依赖真实外部站点稳定性。
