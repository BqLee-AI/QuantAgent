# 04. 数据库与持久化设计

## 文档状态

**状态**：草案 v0.2  
**范围**：数据库模型边界、持久化对象、迁移策略、审计数据、敏感配置  
**当前约定**：数据库使用 PostgreSQL，ORM 使用 SQLAlchemy 2.x + Alembic  
**不包含**：字段级 DDL、完整索引设计、向量检索、embedding 模型选型、生产归档策略

## 设计原则

- 数据库设计服务运行时闭环，不追求一次性覆盖所有未来能力。
- 关键状态必须可回放，尤其是 Event、插件状态、Decision、Approval、Audit。
- 结构化字段优先，JSONB 用于扩展和原始载荷，不把所有数据都塞进 JSONB。
- ORM model 只负责数据库映射，不直接作为 API DTO、Event DTO 或 Plugin DTO 使用。
- 插件不能直接持有数据库 session，只能通过核心提供的 repository / storage port 访问数据。
- 向量检索和 embedding 不进入初版主线，后续如需要单独设计。

## 总体持久化边界

初版数据库负责保存这些运行时对象：

- 原始事件和标准事件。
- 事件状态流转。
- 插件安装记录、版本、配置和依赖。
- Router Agent 路由结果。
- Agent 运行摘要和工具调用记录。
- 行业分析摘要。
- Scoring / Debate 摘要。
- Decision 结果。
- 通知记录。
- 人工确认记录。
- 审计日志和运行时错误。

暂不持久化：

- 完整模型原始推理链。
- 真实交易订单。
- 复杂回测结果。
- 大规模原始网页快照。
- 向量 embedding。

## Event 持久化

Event 采用三层结构：

```text
raw_events
events
event_state_transitions
```

### `raw_events`

保存 source 插件采集到的原始输入。

用途：

- 保留 RSS、URL、X API、Readability/Jina link reader 等不同 source 的原始载荷。
- 支持回放 source 插件的标准化过程。
- 便于排查原始数据和标准事件不一致的问题。

### `events`

保存系统标准化后的事件。

用途：

- 作为 Router Agent、Industry Plugin、Decision 和 UI 的主事件对象。
- 保存当前事件状态。
- 保存结构化字段，例如来源、标题、正文摘要、时间、实体、标签。
- 使用 JSONB 保存扩展 metadata，但核心查询字段必须结构化。

### `event_state_transitions`

以 append-only 方式记录事件状态变化。

用途：

- 审计事件从 captured 到 routed、analyzing、decision_ready、notified 等状态的全过程。
- 记录状态变化时间、触发模块、原因和错误信息。
- 避免只依赖 `events.status` 当前值导致历史不可追踪。

## 插件持久化

插件系统采用“文件作为插件包来源，数据库作为运行时状态真源”的模型。

### 文件系统职责

插件包中的文件保存静态内容：

```text
plugin.yaml
config.schema.json
src/
README.md
```

这些文件描述插件是什么、如何加载、默认配置 schema 是什么。它们随插件包分发，不代表系统当前运行状态。

### 数据库职责

数据库保存运行时状态：

```text
plugin_records
plugin_versions
plugin_configs
plugin_dependency_records
```

数据库记录系统实际安装了什么插件、当前启用哪个版本、配置是什么、来源是什么、安装路径在哪里、当前状态是什么、最后一次错误是什么。

### 设计规则

- 安装插件时，Registry 读取 `plugin.yaml`，校验后写入数据库。
- 系统运行时以数据库记录判断插件状态，不以实时扫描文件目录作为状态真源。
- 插件代码和 manifest 仍由文件系统或插件包提供。
- 插件配置变更、启停、升级、降级、卸载都必须写入审计日志。
- 同一插件 ID 同一时间只能有一个 active version。

## 分析与决策结果持久化

Agent 和插件输出采用“结构化摘要 + JSONB 原始载荷”的方式保存。

```text
routing_decisions
industry_analyses
scored_analyses
decision_results
```

### 结构化字段

必须结构化保存的字段包括：

- `event_id`
- `plugin_id`
- `plugin_version`
- `confidence_score`
- `risk_flags`
- `recommended_actions`
- `decision_action`
- `status`
- `created_at`

### JSONB 载荷

JSONB 用于保存早期仍在演进的半结构化输出，例如：

- Router 的原因摘要。
- 行业分析摘要。
- 反方观点。
- 证据摘要。
- Scoring 细节。
- Decision audit summary。

约束：

- JSONB 中不得保存完整敏感密钥。
- 不默认保存完整模型原始推理链。
- 后续稳定下来的高频查询字段应迁移为结构化字段。

## 审计日志

审计采用“主表保存当前状态 + append-only audit 表记录变化”的方式。

```text
audit_logs
```

必须记录的动作：

- Event 状态变化。
- 插件安装、升级、降级、启用、停用、卸载。
- 插件配置变更。
- 依赖自动安装。
- Decision 生成。
- Human Approval 确认、拒绝、要求重分析。
- Notification 发送失败或成功。
- Runtime error。

设计规则：

- `audit_logs` 只追加，不更新业务历史。
- 主表用于查询当前状态。
- 审计表用于回放历史变化。
- 对同一个业务动作，写主表和写 audit 应在同一事务边界内完成。

## 敏感配置

敏感配置采用 secret reference 为主、加密入库为辅的策略。

### Secret Reference

数据库默认只保存引用，不保存真实密钥。

```text
api_key_ref: secret://x_api/main
```

初版 secret 来源可以是：

- 环境变量。
- `runtime/config/secrets.*` 本地文件。
- 后续外部 Secret Manager。

### 加密入库

确实必须入库的敏感字段需要加密保存。

约束：

- 插件配置 schema 需要能标记字段是否敏感。
- 日志不得输出敏感字段原文。
- API 响应不得返回敏感字段原文。
- 后台 UI 只能显示 masked value 或 secret reference。

## Migration 目录

Alembic migration 放在核心包内：

```text
packages/core/
  alembic/
    env.py
    script.py.mako
    versions/
  src/quantagent/core/
    db/
      base.py
      session.py
      models/
      repositories/
```

原因：

- 数据模型是核心领域的一部分，不属于 `apps/api`。
- `apps/api`、`apps/worker`、未来 `apps/scheduler` 都会依赖数据库结构。
- 后续如果拆服务，core migration 仍然是共享基础。

## 软删除与数据保留

初版采用关键主表软删除，审计和状态流转 append-only。

### 软删除主表

这些表支持软删除：

- `events`
- `plugin_records`
- `plugin_configs`

### Append-only 表

这些表不做软删除，只追加：

- `event_state_transitions`
- `audit_logs`

### 暂缓项

- 数据保留周期暂不定义。
- 归档策略暂不定义。
- 真实物理删除只允许用于本地开发或明确的维护脚本。

## 初版表分组

### Event 相关

```text
raw_events
events
event_state_transitions
```

### Plugin 相关

```text
plugin_records
plugin_versions
plugin_configs
plugin_dependency_records
```

### Analysis 相关

```text
agent_runs
agent_run_steps
tool_invocations
routing_decisions
industry_analyses
scored_analyses
decision_results
```

### Human / Notification 相关

```text
approval_records
notification_records
```

### Audit / Runtime 相关

```text
audit_logs
runtime_errors
```

## 初版落地顺序

1. 建立 SQLAlchemy Base、session、repository 基础结构。
2. 建立 Alembic migration 目录。
3. 建立 Event 相关表。
4. 建立 Plugin registry 相关表。
5. 建立 AgentRuntime 运行摘要和工具调用相关表。
6. 建立 Analysis、Decision、Approval、Audit 相关表。
7. 根据实际开发情况补充必要索引和查询优化。

## 暂缓能力

- 向量检索和 embedding。
- 历史相似事件检索。
- 回测结果持久化。
- 大规模原始网页快照存储。
- 生产归档策略。
- 外部 Secret Manager。

## 待确认问题

暂无。用户已确认采用本文档推荐方案。
