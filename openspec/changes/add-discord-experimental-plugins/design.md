## Context

当前仓库已经有 Plugin Registry V1 的 OpenSpec 和最小实现，明确了官方插件必须通过 `plugin.yaml` 注册，并且 `source`、`notification` 是固定插件类型。与此同时，`plugins/` 目录里还没有任何 Discord 官方插件样板，`packages/plugin-sdk` 也仍是占位状态。Issue #110 及其评论已经把范围收敛到“以实验性插件组的方式，在 `plugins/` 内证明 Discord 能发、能收、能单独测试”，因此这次设计重点不是集成 Discord 平台，而是把最小插件协议、目录结构、测试和非目标写清楚，避免实现中扩到核心 HTTP、审批或事件流。

## Goals / Non-Goals

**Goals:**

- 在 OpenSpec 中固定第一版 Discord 官方实验性插件组的拆分方式：一个 `notification` 发送插件，一个 `source` 接收插件。
- 固定接收实现路径为 `Webhook Push`，并明确接收成功后只标准化到插件内 DTO。
- 要求两个插件都通过 `plugin.yaml` + `config.schema.json` 注册和描述配置，且敏感字段必须走 secret reference。
- 要求两个插件都提供独立 mock / fixture / standalone test harness，覆盖成功路径和结构化失败路径。
- 限制主要实现代码在 `plugins/` 内，避免为了支持 Discord 而修改核心 Runtime / API / 审批 / 执行契约。

**Non-Goals:**

- 不定义统一聊天通道模型、核心入站消息契约或新的 Event Bus 接入协议。
- 不实现 Discord bot polling、gateway stream、富交互组件、附件、多 guild 管理或社区运营能力。
- 不要求第一版接收能力直接打通审批回流、自动执行、实时通道或系统主事件流。
- 不新增 plugin SDK、核心 loader、动态 HTTP 路由挂载或运行时依赖安装机制。

## Decisions

### 1. 发送与接收拆成两个官方插件

第一版 SHALL 拆成两个官方插件，而不是一个混合插件或一个目录内的多 manifest 特例：

- `notification` 插件负责 Discord 发送。
- `source` 插件负责 Discord 接收。

这样做的原因是现有设计文档已经把 `notification` 和 `source` 作为固定插件类型，Issue #110 也明确要求优先复用既有类型边界。替代方案是一个单插件组双入口或由 `source` 顺带承担发送，这会模糊类型职责，也不利于独立测试，因此不采用。

### 2. 接收路径固定为 Webhook Push

第一版 Discord 接收 SHALL 走 `Webhook Push` 路径，用 mock inbound payload 和请求头上下文完成插件内验证。替代方案是 bot polling 或 gateway stream，但这两条路径都会引入额外状态管理、频率控制或长连接治理，明显超出本 issue 的实验范围，因此不采用。

### 3. 标准化终点停在插件内 DTO

接收插件 SHALL 只把合法 inbound payload 解析为插件内标准化 DTO，并返回结构化成功/失败结果。它 MUST NOT 在本轮直接定义系统级 `RawEvent`、SourceBinding 对象、API DTO 或 Event Bus 接入。这样可以证明“能收、能解析、能报错”，同时避免为了 Discord 接收反向设计核心契约。替代方案是直接对齐 `RawEvent`，但当前仓库还没有为 push source 建立稳定实现路径，会把本轮 spec 扩大到核心 source 运行时，因此不采用。

### 4. 配置只暴露最小 secret reference 与 allowlist

两个插件的 `config.schema.json` SHALL 只描述本轮验收需要的最小配置：

- 发送侧至少需要 webhook secret reference。
- 接收侧至少需要签名校验所需 secret/public key reference，以及可选 guild/channel allowlist。

schema MUST NOT 内嵌真实 secret、真实 webhook URL 或私有频道信息。替代方案是直接让 README 约定原始环境变量名而不做 schema 约束，但这会削弱 Registry 扫描和后续配置治理，因此不采用。

### 5. 主要实现代码控制在 plugins 内，核心系统只允许“被动复用”

本 change SHALL 要求主要实现代码、README、fixtures 和 tests 都落在 `plugins/` 范围内。可以被动复用现有 Python 测试 harness 或 Registry 扫描能力，但 MUST NOT 为了 Discord 插件去修改核心 Runtime / API / 审批 / 执行契约。如果实现过程中发现接收路径必须依赖稳定 HTTP 挂载点、统一聊天通道或核心入站模型，则应停止扩 scope，并先补新的 OpenSpec change。

### 6. 验收默认依赖 mock / fixture，不阻塞于真实 Discord

默认验收 SHALL 依赖插件级 mock / fixture / standalone tests。真实 Discord 手工 smoke 可以作为补充验证，但 MUST NOT 成为默认阻塞条件。这样做可以避免本 change 把外部环境、凭证和网络波动引入 OpenSpec 验收门槛。

## Risks / Trade-offs

- [Risk] 只做到插件内 DTO，可能让 reviewer 觉得“接收还没真正接进系统”。
  -> Mitigation：在 proposal、spec 和 README 中明确本轮目标是实验性插件样板，不是系统级入站契约。

- [Risk] Webhook Push 与未来真实 Discord 接入路径可能不同。
  -> Mitigation：将其明确标记为第一版最小实验路径；如果后续需要 polling/gateway，再另开 change 收敛。

- [Risk] 当前仓库没有成熟 plugin SDK，插件实现接口可能带有临时性。
  -> Mitigation：spec 只约束插件目录、manifest、config schema、测试和行为边界，不提前发明长期 SDK 契约。

- [Risk] 为了验证接收路径，实施者可能尝试改 API 路由或核心 loader。
  -> Mitigation：tasks 明确把“发现必须改核心契约则停止并转新 change”作为 review gate，而不是施工细节。
