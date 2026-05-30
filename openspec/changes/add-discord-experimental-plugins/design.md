## Context

当前仓库已经有 Plugin Registry V1 的最小实现，也已经在 `plugins/` 下落了 Discord 发送与接收样板。但这条链路是按“双插件拆分”推进的：发送落在 `notification`，接收落在 `source`。本轮会议收敛的新要求是“尽量完善为一个插件”，而 Issue #110 本身只要求“能收发、尽量只改 `plugins/`、可单独测试”，并没有强制拆成两个插件。

更上游的 `official-plugin-v1-main-chain` 也把 Discord 表述为单数语义的 Discord 插件。因此，本 change 的目标不是重新发明插件类型体系，而是把 Discord 的第一版实验交付从两个官方插件收口成一个官方插件，同时保持现有 Registry、API ingress 和测试仍可最小闭环。

## Goals / Non-Goals

**Goals:**

- 在 OpenSpec 中固定第一版 Discord 官方实验能力采用单插件交付，而不是两个独立插件。
- 保持 Discord 插件仍通过单个 `plugin.yaml`、单个 `config.schema.json` 和单个 plugin id 进入 Registry。
- 让该插件在同一边界内承接低风险发送和低风险接收能力，并提供统一 README、standalone tests 和 smoke 脚本。
- 允许 API ingress 和测试以 capability/handler 为准调用 Discord 接收逻辑，而不是依赖旧的 source-type 假设。
- 保持主要实现代码仍优先收敛在 `plugins/` 内；API 与 core 只做最小兼容改造。

**Non-Goals:**

- 不新增新的 plugin type，不把 Registry 改成多主类型模型。
- 不引入统一聊天通道模型、核心入站消息契约或新的 Event Bus 接入协议。
- 不实现 Discord bot polling、gateway stream、富交互组件、附件、多 guild 管理或社区运营能力。
- 不要求第一版接收能力直接打通审批回流、自动执行、实时通道或系统主事件流。
- 不把 Discord 插件扩成策略、审批或交易执行入口。

## Decisions

### 1. 第一版 Discord 官方实验能力收敛为一个官方插件

第一版 SHALL 使用一个官方 Discord 插件，而不是“发送插件 + 接收插件”两个独立插件。

该插件采用：

- 一个官方插件目录
- 一个 `plugin.yaml`
- 一个 `config.schema.json`
- 一个 plugin id

这样做的原因是：

- 会议评审希望把同一渠道的收发能力尽量收敛，而不是维持测试期的临时拆分。
- Issue #110 真正关心的是“插件能单独测试、能够收发消息”，并未要求必须分成两个插件。
- `official-plugin-v1-main-chain` 把 Discord 表述为单数插件，更接近当前方向。

替代方案是保留两个插件，再通过 README 或插件组概念把它们包装成“一个能力”。这个方案仍会让 Registry、测试、API 配置和 reviewer 心智维持双实体，不采用。

### 2. 单插件仍沿用既有 plugin type，不扩展新的类型模型

本轮单插件 SHALL 继续沿用既有 plugin type 体系，不新增 `communication`、`chat` 或其他新类型。为保持最小兼容，Discord 插件 SHOULD 挂在 `notification` 类型下，并通过 capabilities 与处理器暴露接收能力。

原因：

- 当前 Registry、API schema 和设计文档都假设 `type` 是单值枚举。
- 为了 Discord 第一版去扩展新的 plugin type，会把范围扩大到 Registry、管理台、API 契约和更多设计文档。
- Discord 接收在本轮仍被限制为低风险交互与通知入口，不需要借此重写整个 source/runtime 模型。

代价是：接收能力不再等价于“所有接收类插件都必须是 `source` 类型”。本轮通过 capability 与显式 handler 校验收口，而不是继续用 type 代理行为。

### 3. API ingress 以 capability/handler 校验 Discord 接收能力

真实 Discord ingress SHALL 不再把“目标插件必须是 `source` 类型”作为唯一门槛，而改为：

- 通过配置定位单一 Discord plugin id
- 确认 record 合法可加载
- 确认插件暴露 `receive_request(...)` 处理器
- 确认 manifest capability 集合包含 Discord 接收所需能力

这样符合本轮“单插件但可接收”的目标，也避免把接收逻辑重新拆回第二个 manifest。

### 4. 配置契约统一到一个 schema

单插件 `config.schema.json` SHALL 同时描述发送与接收需要的最小配置：

- 发送侧：`webhook_secret_ref`、`timeout_seconds`
- 接收侧：`public_key_ref` / `public_key`、`response_text`、allowlist、timestamp tolerance

schema MUST NOT 内嵌真实 secret、真实 webhook URL、真实私钥或私有 guild/channel 信息。

### 5. 目录与文件规划

单插件实现 SHOULD 统一收敛到一个官方目录，例如：

```text
plugins/notifications/discord/
  plugin.yaml
  config.schema.json
  README.md
  discord_plugin.py
  smoke_send.py
  smoke_receive.py
  tests/
```

文件职责：

- `plugin.yaml`：单插件 manifest 真源
- `config.schema.json`：统一配置契约
- `discord_plugin.py`：发送与接收处理器、DTO、结构化结果
- `smoke_send.py` / `smoke_receive.py`：各自独立补充验证入口
- `tests/`：发送、接收和结构化失败路径测试

### 6. 兼容性迁移允许最小破坏性收口

本 change 允许把旧的发送/接收双插件收敛为新的官方 plugin id `quantagent.official.notification.discord`。测试、README、API 默认配置和 Registry 扫描期望需要同步更新。

本轮不承诺向后兼容保留两个旧 plugin id；它们属于实验性样板，允许按新真源直接收口。

## Data / Failure Flow

发送路径：

```text
validated config + secret ref
  -> Discord plugin send_text
  -> webhook request
  -> structured send result
```

接收路径：

```text
API ingress
  -> configured Discord plugin id
  -> Registry record + entrypoint loader
  -> plugin.receive_request(config, headers, body)
  -> signature validation + payload parse
  -> interaction response + plugin DTO
```

关键失败路径：

- plugin id 不存在 / record 非法
- 插件无 `receive_request` handler
- manifest capability 不符合预期
- webhook secret 缺失或不可解析
- Discord 公钥配置缺失
- 签名、时间戳、allowlist、payload 校验失败

这些失败都必须返回结构化结果，且不得泄露 secret、公钥原文、完整 payload 或内部路径。

## Risks / Trade-offs

- [Risk] 把接收能力放到 `notification` 类型下，会弱化“接收即 source”这条旧心智。
  -> Mitigation：在 spec、README 和 API 注释中明确，这是 Discord 单插件的定向兼容，不是对所有 push source 的普遍结论。

- [Risk] 单插件 schema 会同时包含发送与接收字段，看上去比拆分方案更宽。
  -> Mitigation：字段仍然只覆盖第一版最小能力，不顺手加入 Bot token、guild 管理或 followup API。

- [Risk] 旧测试和默认配置大量写死旧 plugin id。
  -> Mitigation：本轮显式更新默认配置、Registry 测试和 ingress 测试，把实验性旧 id 一次性收口。
