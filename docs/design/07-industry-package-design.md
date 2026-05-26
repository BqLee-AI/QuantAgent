# 07. Industry Package 设计

## 文档状态

**状态**：草案 v0.2  
**范围**：行业包插件结构、组合插件模型、SourceBinding、行业 Agent、行业工具、Skill Registry、评分规则、市场映射、测试评估、隐私边界、多行业冲突处理  
**当前约定**：行业包是 `industry` 类型插件；行业包是可包含代码的组合插件/整合包；行业包不能绕过 Event Bus、AgentRuntime、ToolRegistry、Skill Registry 和 Decision  
**不包含**：石油/半导体具体业务规则、复杂知识图谱系统、交易执行细节

## 设计原则

- 行业包通过 `plugin.yaml` 注册，禁止核心代码硬编码注册。
- 行业包可以包含代码，不是纯配置包。
- 行业包引用数据源时，使用 SourceBinding。
- 行业包内置工具必须注册到 ToolRegistry。
- 行业包内置 Skill 必须注册到 Skill Registry。
- AgentDefinition 可以绑定不同 Skill，但只能引用 Skill Registry 中已注册且已授权的 Skill。
- Agent 运行统一走 AgentRuntime。
- 行业包输出必须符合统一 `IndustryAnalysis` 结构。
- 行业包只能提供分析、评分 hint、市场映射、交易计划草案和执行请求，不能绕过 Decision / Policy Gate 直接执行。

## 行业包定位

行业包是领域能力整合包，可以整合：

- SourceBinding templates。
- AgentDefinition。
- 标准 Skill 包。
- 行业专用工具。
- 第三方 API adapter。
- scoring hints。
- market mapping。
- fixture events。
- config schema。

以石油行业为例，行业包可能不仅订阅 RSS 和 X API，还会内置或依赖航运数据工具、库存数据工具、OPEC 数据工具。这些工具可以调用外部 API，也可能需要 API key。它们由行业包声明和实现，但必须注册到 ToolRegistry，由 AgentRuntime 按权限注入给 Agent。

行业包可以写代码，但代码边界必须清晰：

- 可以实现行业专用 tool。
- 可以实现行业专用 normalizer / adapter。
- 可以实现 scoring hints 计算。
- 可以实现 market mapping loader。
- 不能直接启动 source 轮询。
- 不能直接绕过 AgentRuntime 创建 Agent。
- 不能直接绕过 ToolRegistry 暴露工具。
- 不能直接绕过 Skill Registry 注入 Skill。
- 不能直接绕过 Decision 调用 broker。

## SourceBinding

行业包必须声明 required / optional source dependencies 和 SourceBinding templates。

```yaml
source_bindings:
  - source_plugin_id: quantagent.official.source.rss
    required: true
    config_template: rss.oil.yaml
  - source_plugin_id: quantagent.official.source.readability
    required: false
    config_template: readability.default.yaml
```

设计原因：

- 行业包需要知道自己默认依赖哪些 source。
- SourceBinding 是行业包和 source 插件之间的连接点。
- 同一个 source 插件可以被多个行业包以不同关键词、账号和频率复用。
- optional source 可以支持增强能力，例如 Jina link reader 作为 Readability 的备选。

## AgentDefinition

行业包可以自带 AgentDefinition，但必须由核心 AgentRuntime 执行。

```text
agents/
  oil_supply_analyst.md
  geopolitical_risk_analyst.md
```

AgentDefinition 使用 Markdown + frontmatter，并可以绑定工具和 Skill。

```yaml
tools:
  - quantagent.official.industry.oil.tool.shipping_tracker
skills:
  - quantagent.official.skill.oil-market-analysis
  - quantagent.official.skill.geopolitical-risk
```

约束：

- AgentDefinition 只能声明工具和 Skill 需求。
- 工具是否可用由 ToolRegistry 和权限策略决定。
- Skill 是否可用由 Skill Registry 和授权策略决定。
- Agent 不能直接写 API key、账户信息或敏感配置。

## 行业工具

行业包可以内置自定义工具和 API adapter，但必须注册到 ToolRegistry。

示例：

```text
plugins/industries/oil/
  tools/
    shipping_tracker.py
    opec_calendar.py
    inventory_lookup.py
```

工具注册示例：

```text
quantagent.official.industry.oil.tool.shipping_tracker
quantagent.official.industry.oil.tool.opec_calendar
quantagent.official.industry.oil.tool.inventory_lookup
```

约束：

- 工具参数必须有 schema。
- 工具输出必须可序列化。
- 工具调用必须审计。
- 工具需要的 API key 通过 config schema 声明，并使用 secret reference。
- 高风险工具必须受 human approval / Policy Gate 控制。
- 行业包工具不能直接绕过 broker 或 Decision。

## Skill Registry

行业知识不做复杂知识图谱，采用标准 Skill 包。

Skill 来源分三类：

```text
plugins/skills/                  # 官方通用 Skill
plugins/industries/<industry>/skills/  # 行业包内置 Skill
runtime/skills/                  # 第三方、社区、私有或用户安装 Skill
```

Skill Registry 负责：

- 扫描和注册 Skill 包。
- 校验 Skill 标准结构。
- 读取 `SKILL.md` frontmatter。
- 维护 Skill 版本和来源。
- 管理官方、行业包内置、runtime/private Skill 的命名空间。
- 为 AgentRuntime 提供授权后的 Skill 列表。

标准 Skill 包结构：

```text
oil-market-analysis/
  SKILL.md
  references/
    causal-rules.md
    glossary.md
  assets/
  scripts/
```

`SKILL.md` 必须包含 YAML frontmatter：

```markdown
---
name: oil-market-analysis
description: Use for oil market event analysis, supply-demand reasoning, Brent/WTI impact assessment, and oil-related trading thesis generation.
---

# Oil Market Analysis
```

命名空间建议：

| 来源 | 示例 |
| --- | --- |
| 官方通用 Skill | `quantagent.official.skill.market-structure` |
| 行业包内置 Skill | `quantagent.official.industry.oil.skill.oil-market-analysis` |
| 社区 Skill | `community.<author>.skill.<name>` |
| 私有 Skill | `private.<org>.skill.<name>` |

AgentRuntime 加载 Skill 时：

- 先检查 AgentDefinition 声明的 skill id。
- 通过 Skill Registry 验证 skill 是否存在且已授权。
- 读取 `SKILL.md` 的 metadata 和主体说明。
- 仅在需要时加载 `references/`、`assets/`、`scripts/`。

Skill 不负责：

- 直接执行工具。
- 直接给出交易执行决策。
- 替代 IndustryAnalysis 输出 schema。
- 绕过 ToolRegistry 或 Decision。

## 行业主 Agent 行动模型

行业包通常包含一个或多个主 Agent。主 Agent 不是直接调用 Python 服务，而是通过工具完成所有外部行动。

石油行业示例：

```text
Oil Main Agent
  -> tool: call_subagent(oil_supply_analyst)
  -> tool: call_subagent(geopolitical_risk_analyst)
  -> tool: shipping_tracker
  -> tool: opec_calendar
  -> tool: run_debate
  -> tool: generate_trade_plan
  -> tool: request_monitoring
  -> tool: notify_user
  -> tool: request_broker_action
```

主 Agent 可以产出：

- 行业影响判断。
- 证据和反方观点。
- confidence score。
- risk flags。
- 初步交易计划。
- 止盈止损建议。
- 盯盘或特征监控计划。
- 是否建议通知用户。
- 是否请求自动执行。

交易相关请求必须通过 broker tool，且 broker tool 必须执行权限、评分、风控和用户配置检查。

## Market Mapping

市场映射独立为 mapping 文件，不能只写在 prompt 里。

```text
mappings/
  markets.yaml
  instruments.yaml
```

设计原因：

- Decision 和 UI 需要稳定读取市场、标的和候选工具。
- 交易执行细节不能藏在 prompt 里。
- broker 偏好只是建议，最终能否执行仍由 Decision 和 broker policy 决定。

## Scoring Hints

评分采用“核心统一评分框架 + 行业包 scoring hints”。

行业包可以提供：

- 行业特有风险因子。
- 证据质量要求。
- 权重建议。
- 置信度校准提示。
- 高风险事件标记。

核心系统负责：

- 统一置信度区间。
- 统一风险标记。
- 统一 Decision 输入。
- 防止第三方行业包自定义不可治理的最终执行分数。

## 配置和隐私

官方默认配置可以公开，用户覆盖和私有策略默认进入 runtime / DB。

敏感内容包括：

- 私有关键词。
- 私有账号列表。
- 私有行业逻辑。
- 付费数据源 API key。
- 交易策略偏好。
- broker 配置。

规则：

- 敏感字段不得进入插件代码或 manifest。
- 敏感字段通过 config schema 声明。
- 运行时使用 secret reference。
- 后台 UI 需要区分官方默认配置和用户覆盖配置。

## 多行业冲突处理

多个行业包同时命中同一事件时，采用多行业包独立分析，Scoring / Debate 聚合冲突和共识。

流程：

```text
Event
  -> Router Agent
  -> Industry Package A Analysis
  -> Industry Package B Analysis
  -> Scoring / Debate
  -> ScoredAnalysis
  -> Decision
```

设计原因：

- 事件驱动交易经常跨行业。
- 系统需要解释不同 Agent 的冲突，而不是静默选择一个。
- Decision 应基于聚合后的 ScoredAnalysis，而不是单个行业包自说自话。

## 测试和评估

行业包必须提供 fixture events 和 expected output shape。

```text
evals/
  fixture_events.yaml
  expected_shapes.yaml
```

初版要求：

- 至少覆盖一个 happy path。
- 至少覆盖一个低置信度或无关事件。
- 校验 IndustryAnalysis schema。
- 校验关键字段存在。
- 不要求复杂自动评分平台。

## Industry Package 结构

```text
plugins/industries/oil/
  plugin.yaml
  agents/
    oil_supply_analyst.md
    geopolitical_risk_analyst.md
  tools/
    shipping_tracker.py
    opec_calendar.py
    inventory_lookup.py
  skills/
    oil-market-analysis/
      SKILL.md
      references/
        causal-rules.md
        glossary.md
    geopolitical-risk/
      SKILL.md
      references/
        escalation-patterns.md
  mappings/
    markets.yaml
    instruments.yaml
  evals/
    fixture_events.yaml
    expected_shapes.yaml
  config.schema.ts
  config.schema.json
  README.md
```

## Manifest 扩展

```yaml
id: quantagent.official.industry.oil
name: Oil Industry Package
type: industry
version: 0.1.0
entrypoint: oil_plugin:plugin

dependencies:
  plugins:
    - id: quantagent.official.source.rss
      version: ">=0.1.0"
    - id: quantagent.official.source.readability
      version: ">=0.1.0"

source_bindings:
  - source_plugin_id: quantagent.official.source.rss
    required: true
    config_template: rss.oil.yaml
  - source_plugin_id: quantagent.official.source.readability
    required: false
    config_template: readability.default.yaml

agents:
  - agents/oil_supply_analyst.md
  - agents/geopolitical_risk_analyst.md

tools:
  - id: quantagent.official.industry.oil.tool.shipping_tracker
    entrypoint: tools.shipping_tracker:tool
    risk_level: medium
    config_required:
      - shipping_api_key_ref
  - id: quantagent.official.industry.oil.tool.opec_calendar
    entrypoint: tools.opec_calendar:tool
    risk_level: low

skills:
  - id: quantagent.official.industry.oil.skill.oil-market-analysis
    path: skills/oil-market-analysis
  - id: quantagent.official.industry.oil.skill.geopolitical-risk
    path: skills/geopolitical-risk

market_mapping:
  markets: mappings/markets.yaml
  instruments: mappings/instruments.yaml

output_schema: industry_analysis.schema.json
```

## IndustryAnalysis 输出

所有行业包必须输出统一结构：

```text
IndustryAnalysis
  event_id
  industry_plugin_id
  industry_plugin_version
  impact_summary
  first_order_impacts
  second_order_impacts
  affected_markets
  affected_instruments
  evidence
  counter_arguments
  confidence_score
  recommended_actions
  trade_plan_draft
  monitoring_plan
  risk_flags
  requires_verification
  metadata
```

约束：

- `confidence_score` 是行业包分析置信度，不是最终执行置信度。
- `recommended_actions` 是建议，不是可直接执行指令。
- `trade_plan_draft` 是交易计划草案，不是最终执行命令。
- `monitoring_plan` 是盯盘或特征监控建议，可以交给 monitoring tool / scheduler 进一步处理。
- `affected_instruments` 必须来自结构化 market mapping 或被明确标记为推测。
- 行业包不能直接调用 broker。

## 初版实现范围

必须实现：

- Industry Package manifest 扩展。
- SourceBinding template。
- AgentDefinition 引用。
- 行业包内置工具注册。
- Skill Registry。
- 行业包内置 Skill 注册。
- 官方通用 Skill 注册。
- runtime/private Skill 注册。
- market mapping 文件。
- scoring hints schema。
- fixture events 和 expected output shape。
- IndustryAnalysis schema 校验。

暂缓实现：

- 复杂行业知识图谱系统。
- 在线 Skill 编辑和审核流程。
- 复杂行业评分公式。
- 行业包市场。
- 自动交易 broker 深度集成。

## 待确认问题

暂无。用户已确认本文档核心方向，Skill 采用标准 Skill 包结构并进入 Skill Registry。
