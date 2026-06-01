# Discord Notification

这是第一版官方实验性 Discord 单插件，在同一插件边界内承接低风险发送与接收能力。

## 当前支持

- 使用 `plugin.yaml` + `config.schema.json` 注册为单个官方 `notification` 类型插件。
- 通过纯 Python API 发送最小文本消息到 Discord webhook。
- 接收 Discord `interaction webhook` 请求，并完成官方 `Ed25519` 验签、`PING` 握手与最小 `APPLICATION_COMMAND` 响应。
- 通过 `secrets` 映射解析 `webhook_secret_ref` 或 `public_key_ref`，避免把真实配置写进 schema。
- 通过 mock transport、签名 fixture 和 standalone smoke 独立验证发送与接收路径。

## 配置

`config.schema.json` 统一描述本轮最小字段：

- `webhook_secret_ref`: 指向完整 Discord webhook URL 的 secret reference。
- `timeout_seconds`: 发送请求超时。
- `public_key_ref`: 指向 Discord application public key 的引用。
- `public_key`: 宿主在真实 ingress 场景下注入的已解析公钥。
- `response_text`: 对支持的 command interaction 返回的最小确认文本。
- `timestamp_tolerance_seconds`: 签名时间戳容忍窗口。
- `guild_allowlist` / `channel_allowlist`: 可选 allowlist。

示例配置：

```json
{
  "webhook_secret_ref": "discord.webhooks.primary",
  "timeout_seconds": 5,
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
  "discord.webhooks.primary": "https://discord.example.invalid/api/webhooks/...",
  "discord.interactions.public_key": "<discord-application-public-key>"
}
```

## 独立测试

运行统一插件测试：

```bash
uv run python -m unittest discover -s plugins/notifications/discord/tests -p 'test_*.py'
```

## 真实 Discord 接入方式

当前版本需要通过 `apps/api` 提供的通用 notification ingress HTTP host 才能接收真实 Discord 回调：

- `POST /api/v1/integrations/notifications/ingress`
- API 层负责读取原始 body、请求头和运行时配置。
- API 层通过 Registry + manifest `entrypoint` 加载本插件对象。
- 本插件负责 webhook 发送、官方 `Ed25519` 验签、`PING`/command 解析和 interaction response 生成。
- API host 不理解 Discord 私有结果码；HTTP 状态码与响应体都由插件返回。

本地最小配置示例：

```bash
NOTIFICATION_INGRESS_ENABLED=true
NOTIFICATION_INGRESS_PLUGIN_ID=quantagent.official.notification.discord
NOTIFICATION_INGRESS_PLUGIN_CONFIG='{
  "public_key": "<discord-application-public-key>",
  "response_text": "QuantAgent received your Discord interaction.",
  "guild_allowlist": ["guild-1", "guild-2"],
  "channel_allowlist": ["channel-1", "channel-2"]
}'
```

然后在 Discord Developer Portal 中把 Interactions Endpoint URL 指向：

```text
https://<your-public-host>/api/v1/integrations/notifications/ingress
```

## 真实 Smoke Test

发送补充验证：

```bash
uv run python plugins/notifications/discord/smoke_send.py
```

接收补充验证：

```bash
NOTIFICATION_INGRESS_TEST_PRIVATE_KEY=<hex-private-key> \
uv run python plugins/notifications/discord/smoke_receive.py
```

注意：

- 这两条都属于补充验证，不是默认阻塞验收项。
- 不要把真实 webhook URL、公钥私钥、bot token 或私有 guild/channel 信息提交到仓库。
- 发送 smoke 会产生真实 Discord 消息；接收 smoke 会向配置的 ingress endpoint 发送真实 HTTP 请求。
- Notification Plugin Ingress V1 的模型需要兼容 webhook、websocket、polling；当前 Discord 样板只实现 webhook 所需的基础 HTTP host 接入。

## 非目标

- 不支持 polling、gateway、富消息、附件、多 guild 管理、审批回流、自动执行、统一聊天通道或主事件流接入。
- 不支持 message component、autocomplete、modal submit、followup message 或延迟回调链路。
- 不在 README、schema 或测试样例中暴露真实 webhook URL、私钥或私有频道信息。
