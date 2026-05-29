# Discord Interaction Webhook Source

这是第一版官方实验性 Discord 接收插件，职责是接收真实 Discord `interaction webhook` 请求，在插件边界内完成官方签名校验、最小解析，并返回 Discord 可接受的首个 interaction response。

## 当前支持

- 使用 `plugin.yaml` + `config.schema.json` 注册为 `source` 类型插件。
- 接收 Discord `interaction` 风格 JSON payload。
- 使用 Discord 官方 `Ed25519` 请求签名校验。
- 支持 Discord Developer Portal 的 `PING` 验证握手。
- 对最小支持的 `APPLICATION_COMMAND` 返回合法 interaction response。
- 输出插件内 DTO，但仍不直接接入 Event Bus、`RawEvent`、审批或自动执行链路。

## 配置

`config.schema.json` 只声明本轮必需字段：

- `public_key_ref`: 指向 Discord application public key 的配置引用。
- `response_text`: 对支持的 command interaction 返回的最小确认文本。
- `guild_allowlist`: 可选 guild allowlist。
- `channel_allowlist`: 可选 channel allowlist。

示例配置：

```json
{
  "public_key_ref": "discord.interactions.public_key",
  "response_text": "QuantAgent received your Discord interaction.",
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
  "discord.interactions.public_key": "<discord-application-public-key>"
}
```

## 独立测试

运行接收插件测试：

```bash
uv run python -m unittest discover -s plugins/sources/discord-interaction-webhook/tests -p 'test_*.py'
```

## 真实 Discord 接入方式

当前版本需要通过 `apps/api` 提供的 HTTP ingress 才能接收真实 Discord 回调：

- `POST /api/v1/integrations/discord/interactions`
- API 层负责读取原始 body、请求头和运行时配置。
- API 层通过 Registry + manifest `entrypoint` 加载本插件对象。
- 本插件负责官方 `Ed25519` 验签、`PING`/command 解析和 interaction response 生成。
- 当前 API ingress 直接传入已解析的 runtime config；不会自动读取本插件 schema 中的 `public_key_ref`。`public_key_ref` 仍用于 standalone test 或未来平台配置接入。

本地最小配置示例：

```bash
DISCORD_INTERACTIONS_ENABLED=true
DISCORD_INTERACTIONS_PLUGIN_ID=quantagent.official.source.discord_interaction_webhook
DISCORD_INTERACTIONS_PUBLIC_KEY=<discord-application-public-key>
DISCORD_INTERACTIONS_RESPONSE_TEXT=QuantAgent received your Discord interaction.
DISCORD_INTERACTIONS_GUILD_ALLOWLIST=guild-1,guild-2
DISCORD_INTERACTIONS_CHANNEL_ALLOWLIST=channel-1,channel-2
```

然后在 Discord Developer Portal 中把 Interactions Endpoint URL 指向：

```text
https://<your-public-host>/api/v1/integrations/discord/interactions
```

Discord 会先发送 `PING` 验证请求；验证通过后才会继续发送真实 interaction。

## 真实 Smoke Test

建议至少完成两步：

1. 在可公网访问的 HTTPS 地址上启动 API，并启用上面的 Discord 配置。
2. 在 Discord Developer Portal 保存 Interactions Endpoint URL，确认 `PING` 校验通过。

如果后续还定义了实际 slash command，再执行一次最小 command smoke test，确认 endpoint 返回的 interaction response 能被 Discord 接受。

## 本地签名 Smoke

如果你还没把公网 HTTPS 地址接给 Discord，可以先做一次本地签名联调：

1. 生成一组测试私钥/公钥，把公钥填到 `DISCORD_INTERACTIONS_PUBLIC_KEY`。
2. 启动 API。
3. 设置测试私钥后执行：

```bash
DISCORD_INTERACTIONS_TEST_PRIVATE_KEY=<hex-private-key> \
uv run python plugins/sources/discord-interaction-webhook/smoke_receive.py
```

脚本默认使用当前 Unix 时间戳签名；只有在排查边界场景时才需要显式覆盖 `DISCORD_INTERACTIONS_TEST_TIMESTAMP`。

脚本会对本地 endpoint 发送一条带官方 `Ed25519` 风格签名的请求，并打印：

- `derived_public_key`：由测试私钥推导出的公钥，应该与你配置到 API 的 `DISCORD_INTERACTIONS_PUBLIC_KEY` 一致。
- `http_status`
- `response_body`

## 非目标

- 不支持 polling、gateway、审批回流、自动执行、统一聊天通道或主事件流接入。
- 不支持 message component、autocomplete、modal submit、followup message 或延迟回调链路。
- 不在 README、schema 或 fixtures 中暴露真实 token、public key 私有配置或私有 guild/channel 信息。
