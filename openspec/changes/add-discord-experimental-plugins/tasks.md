## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `add-discord-experimental-plugins` change 的 proposal、design、specs、tasks 和必要元数据。
- [x] 1.2 在 PR 说明中写清楚：本 PR 只定义第一版 Discord 官方实验插件组边界，不实现代码、不改核心 Runtime / API / 审批契约。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再进入实现 PR。
- [x] 1.4 根据会议收敛结果，把 Discord 官方实验能力从双插件方案改写为单插件方案，并同步更新相关 change 真源。

## 2. 插件边界与目录结构

- [x] 2.1 将 Discord 发送与接收实现收敛到同一个官方插件目录、单个 `plugin.yaml` 和单个 `config.schema.json`。
- [x] 2.2 统一 README、standalone smoke 与测试入口，明确发送与接收都由同一插件承接。
- [x] 2.3 在实现评审时确认主要代码改动仍优先控制在 `plugins/` 范围内；若发现必须改核心契约，则停止实现并转为新的 OpenSpec change。

## 3. Discord 发送与接收能力

- [x] 3.1 保留最小 Discord 发送入口，支持用有效配置向 webhook 或 mock endpoint 发送纯文本消息。
- [x] 3.2 保留最小 Discord 接收入口，支持官方签名校验、`PING`、最小 command 解析和结构化响应。
- [x] 3.3 为发送与接收两条路径统一返回结构化成功/失败结果，且结果不泄露敏感值。
- [x] 3.4 为同一插件提供独立 mock / fixture / standalone tests，覆盖发送、接收和关键失败场景。

## 4. 兼容性收口

- [x] 4.1 更新 API ingress、Registry 测试和默认配置中的旧 plugin id 与旧 source-type 假设。
- [x] 4.2 以 capability/handler 校验替代“Discord 接收必须是 source 插件”的旧判断。

## 5. 验证与收口

- [x] 5.1 运行与改动范围匹配的 Python 测试，证明单插件 manifest / schema 可被 Registry 扫描，且发送与接收独立测试通过。
- [x] 5.2 运行 `openspec validate add-discord-experimental-plugins --type change --strict --json` 并确保结果通过。
- [ ] 5.3 如本地具备 Discord 测试环境，可补一次真实收发 smoke test，并在实现 PR 中明确标记为“补充验证”而非默认验收前提。
