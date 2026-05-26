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

## 关于真实 Discord 联调

当前版本还不支持直接对接真实 Discord interaction webhook 做端到端联调，原因是这版实现刻意停在实验性插件边界：

- 当前签名校验使用的是插件内 HMAC fixture，不是 Discord 正式的 `Ed25519` 验签。
- 当前仓库没有把这个插件挂进稳定 HTTP ingress，因此 Discord 也没有可回调的实际 endpoint。

如果后续要支持真实 Discord 接收联调，至少需要新增两类能力，并通过新的 OpenSpec change 审核：

- 真实 Discord `Ed25519` 请求签名校验。
- 一个可暴露给 Discord Developer Portal 的实际 webhook ingress 和路由挂载方式。

## 非目标

- 不直接验证真实 Discord Ed25519 签名。
- 不支持 polling、gateway、审批回流、自动执行、统一聊天通道或主事件流接入。
- 不在 README、schema 或 fixtures 中暴露真实 token、signing secret 或私有 guild/channel 信息。
