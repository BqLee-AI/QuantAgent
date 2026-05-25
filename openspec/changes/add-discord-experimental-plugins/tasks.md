## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `add-discord-experimental-plugins` change 的 proposal、design、specs、tasks 和必要元数据。
- [x] 1.2 在 PR 说明中写清楚：本 PR 只定义第一版 Discord 官方实验插件组边界，不实现代码、不改核心 Runtime / API / 审批契约。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。

## 2. 插件边界与目录结构

- [x] 2.1 在 `plugins/notifications/` 和 `plugins/sources/` 内分别建立 Discord 发送与接收插件目录，沿用官方插件命名空间与 `plugin.yaml` 注册方式。
- [x] 2.2 为两个插件分别编写 `config.schema.json`，只声明本轮验收需要的最小 secret reference 和可选 allowlist 字段。
- [x] 2.3 为两个插件分别编写 README，说明实验范围、配置方式、独立测试方法和明确非目标。
- [x] 2.4 在实现评审时确认主要代码改动仍控制在 `plugins/` 范围内；若发现必须改核心契约，则停止实现并转为新的 OpenSpec change。

## 3. Discord 发送插件

- [x] 3.1 实现最小 Discord 发送入口，支持用有效配置向 webhook 或 mock endpoint 发送纯文本消息。
- [x] 3.2 为 webhook 配置缺失、上游错误、超时和网络异常定义结构化失败结果，且结果不泄露敏感值。
- [x] 3.3 为发送插件提供独立 mock / fixture / standalone tests，覆盖 payload 构造、成功发送和失败转换。

## 4. Discord 接收插件

- [x] 4.1 实现基于 Webhook Push 的最小接收入口，接收请求头上下文、配置和 inbound payload。
- [x] 4.2 实现最小鉴权与解析逻辑，把合法消息标准化为插件内 DTO，而不接入 Event Bus 或系统级 `RawEvent`。
- [x] 4.3 为鉴权失败、payload 非法、配置缺失和不支持的输入类型返回结构化失败结果。
- [x] 4.4 为接收插件提供独立 fixture / standalone tests，覆盖合法消息、鉴权失败、payload 非法和配置缺失场景。

## 5. 验证与收口

- [x] 5.1 运行与改动范围匹配的 Python 测试，证明两个插件 manifest / schema 可被 Registry 扫描，且各自独立测试通过。
- [x] 5.2 运行 `openspec validate add-discord-experimental-plugins --type change --strict --json` 并确保结果通过。
- [ ] 5.3 如本地具备 Discord 测试环境，可补一次真实收发 smoke test，并在实现 PR 中明确标记为“补充验证”而非默认验收前提。
