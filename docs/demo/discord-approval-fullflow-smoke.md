# Discord approval fullflow smoke

这个 smoke 用来本地复现：

```text
ActionRequest
-> ApprovalRequest
-> notification.requested
-> Discord webhook send
-> Discord /notify
-> notification.receive
-> ApprovalInput.raw_text
-> ApprovalDecision
```

它是本地受控 demo，不是生产路由。`/api/v1/debug/fullflow` 只在运行 `api-discord-approval-smoke` 命令时存在。

## 前置条件

在仓库根目录 `.env` 中配置：

```text
DISCORD_WEBHOOK_URL=<discord-channel-webhook-url>
NOTIFICATION_INGRESS_ENABLED=true
NOTIFICATION_INGRESS_PLUGIN_ID=quantagent.official.notification.discord
NOTIFICATION_INGRESS_PLUGIN_CONFIG='{"public_key":"<discord-application-public-key>","response_text":"QuantAgent received your Discord interaction."}'
```

注意：

- `DISCORD_WEBHOOK_URL` 只用于发送通知到 Discord 频道。
- `public_key` 必须来自 `/notify` 所属 Discord Application。
- Discord Application 的 Interactions Endpoint URL 必须指向本机 tunnel 的 ingress。
- 不要把真实 webhook URL、public key、bot token 或私有 guild/channel 信息提交到仓库。

## 1. 启动 smoke harness

从仓库根目录运行：

```bash
uv run api-discord-approval-smoke
```

启动成功后会看到类似：

```text
FULLFLOW ... seed action=action-fullflow approval=approval-fullflow status=pending notification_completed=1
FULLFLOW ... notification.completed accepted=True code=SENT message=Discord webhook notification sent.
Uvicorn running on http://127.0.0.1:8000
```

如果 `notification.completed` 不是 `SENT`，先检查 `.env` 中的 `DISCORD_WEBHOOK_URL`。

## 2. 启动公网 tunnel

另开一个终端：

```bash
npx --yes localtunnel --port 8000 --subdomain modern-bags-beam
```

拿到 URL：

```text
https://modern-bags-beam.loca.lt
```

## 3. 配置 Discord Application

在 Discord Developer Portal 中，把 `/notify` 所属 Application 的 Interactions Endpoint URL 设置为：

```text
https://modern-bags-beam.loca.lt/api/v1/integrations/notifications/ingress
```

保存成功说明 Discord PING 已经通过签名校验。

## 4. 查看初始状态

```bash
curl http://127.0.0.1:8000/api/v1/debug/fullflow
```

预期包含：

```json
{
  "approval_id": "approval-fullflow",
  "approval_status": "pending",
  "input_count": 0,
  "notification_completed_count": 1,
  "notification_completed_payloads": [
    {
      "accepted": true,
      "code": "SENT"
    }
  ]
}
```

## 5. 在 Discord 回复 /notify

在 Discord 中选择同一个 Application 的 `/notify`，文本填：

```text
approval_id: approval-fullflow approve
```

## 6. 查看回流结果

再次运行：

```bash
curl http://127.0.0.1:8000/api/v1/debug/fullflow
```

预期结果：

```json
{
  "approval_status": "escalated",
  "input_count": 1,
  "latest_input": {
    "raw_text": "approval_id: approval-fullflow approve"
  },
  "latest_evaluation": {
    "interpreted_intent": "escalate",
    "requires_stronger_confirmation": true
  },
  "latest_decision": {
    "status": "escalated",
    "execution_status": "not_requested"
  },
  "executor_calls": 0
}
```

这是预期行为。Discord 文本 `approve` 属于弱确认，不会直接触发 executor。

## 7. 可选：验证强确认执行分支

Discord 文本确认已经让 `approval-fullflow` 进入终态 `escalated` 后，同一个 approval 的强确认会被忽略。要验证执行分支，请重新启动 smoke harness，然后在发送 `/notify` 前执行：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/debug/fullflow/strong-confirm
```

预期包含：

```json
{
  "decision": {
    "status": "execution_requested",
    "policy_gate_status": "allowed",
    "execution_status": "dry_run_requested"
  },
  "executor_calls": 1,
  "gate_calls": 1
}
```

这一步只调用 fake executor，不代表真实 broker 执行。

## 常见问题

### 访问 /api/v1/debug/fullflow 返回 404

说明你启动的是普通 API，不是 `api-discord-approval-smoke`。这个 debug route 只在 smoke harness 中存在。

### Discord 显示应用程序未响应

通常是本机 API 或 tunnel 停了。先确认：

```bash
curl http://127.0.0.1:8000/api/v1/debug/fullflow
```

再确认公网 URL：

```bash
curl https://modern-bags-beam.loca.lt/api/v1/debug/fullflow
```

### /notify 有回复但 debug 没有 input

通常是你触发的 `/notify` 属于另一个 Discord Application。发 `/notify` 的 App、Developer Portal 里配置 endpoint 的 App、`.env` 里的 `public_key` 必须是同一个 Application。
