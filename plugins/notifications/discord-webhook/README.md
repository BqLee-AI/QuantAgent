# Discord Webhook Notification

这是第一版官方实验性 Discord 发送插件，职责仅限于把最小纯文本消息发送到 Discord webhook 或等价 mock endpoint。

## 当前支持

- 使用 `plugin.yaml` + `config.schema.json` 注册为 `notification` 类型插件。
- 通过纯 Python API 发送最小文本消息。
- 通过 `secrets` 映射解析 `webhook_secret_ref`，避免把真实 webhook URL 写进配置 schema。
- 使用 mock transport 独立验证 payload 构造、成功发送、超时和上游错误转换。

## 配置

`config.schema.json` 只声明本轮必需字段：

- `webhook_secret_ref`: 指向完整 Discord webhook URL 的 secret reference。
- `timeout_seconds`: 可选请求超时。

示例配置：

```json
{
  "webhook_secret_ref": "discord.webhooks.primary",
  "timeout_seconds": 5
}
```

示例 secrets 映射只用于本地 standalone test：

```json
{
  "discord.webhooks.primary": "https://discord.example.invalid/api/webhooks/..."
}
```

## 独立测试

运行发送插件测试：

```bash
uv run python -m unittest discover -s plugins/notifications/discord-webhook/tests -p 'test_*.py'
```

## 非目标

- 不支持富消息、附件、Bot API、guild/channel 管理。
- 不接入核心 Runtime、审批流、交易执行或统一通知中心。
- 不在 README、schema 或测试样例中暴露真实 webhook URL。
