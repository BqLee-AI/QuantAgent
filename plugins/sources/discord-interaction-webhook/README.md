# Discord Interaction Webhook Source

这是第一版官方实验性 Discord 接收插件，职责仅限于接收一条 Discord `interaction webhook` 风格的入站请求，在插件边界内完成最小鉴权、解析并产出插件内 DTO。

## 当前支持

- 使用 `plugin.yaml` + `config.schema.json` 注册为 `source` 类型插件。
- 接收 `interaction` 风格 JSON payload。
- 使用实验性的 HMAC 签名夹具做 standalone 验证，避免在当前阶段引入核心 webhook ingress 或真实 Discord Ed25519 校验依赖。
- 输出插件内 DTO，不直接接入 Event Bus、`RawEvent`、审批或自动执行链路。

## 配置

`config.schema.json` 只声明本轮必需字段：

- `signing_secret_ref`: 指向接收签名 secret 的 secret reference。
- `timestamp_tolerance_seconds`: 可选签名时间窗。
- `guild_allowlist`: 可选 guild allowlist。
- `channel_allowlist`: 可选 channel allowlist。

示例配置：

```json
{
  "signing_secret_ref": "discord.interactions.signing",
  "timestamp_tolerance_seconds": 300,
  "guild_allowlist": [
    "guild-1"
  ],
  "channel_allowlist": [
    "channel-1"
  ]
}
```

示例 secrets 映射只用于本地 standalone test：

```json
{
  "discord.interactions.signing": "integration-secret"
}
```

## 独立测试

运行接收插件测试：

```bash
uv run python -m unittest discover -s plugins/sources/discord-interaction-webhook/tests -p 'test_*.py'
```

## 非目标

- 不直接验证真实 Discord Ed25519 签名。
- 不支持 polling、gateway、审批回流、自动执行、统一聊天通道或主事件流接入。
- 不在 README、schema 或 fixtures 中暴露真实 token、signing secret 或私有 guild/channel 信息。
