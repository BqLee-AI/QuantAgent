# 11. Crawler Source Plugin 边界说明

## 文档状态

**状态**：草案 v0.1  
**范围**：crawler / search / market-data / filing / social 类 Source Plugin 的插件开发边界、配置责任、运行时职责分工、reader fallback 约定  
**不包含**：具体插件实现、调度器实现、数据库模型、API 细节、前端控制台细节

## 设计结论

- 插件开发者只负责 Source Plugin 包本身能力与配置契约，不负责系统接入。
- 插件配置由插件通过 `config.schema.json` 声明，由平台负责校验、保存、启停、调度和审计。
- 运行时平台将校验后的配置作为 DTO / `effective_config` 传给插件；插件只根据该配置执行抓取、解析和标准化。
- 插件输出必须回到平台约定的 source 输出结构，由核心系统负责 `RawEvent` 入库、去重、`SourceBinding`、`Event Bus`、权限和生命周期。
- 对网页或新闻类抓取，初版默认准备 `Jina Reader` 与 `Readability` 两类读取路径，用于兜底和降级。
- 可以复用 GitHub 或其他来源的开源能力，例如 `Fincept Terminal`，但必须包在插件边界后面，不能让核心系统直接耦合第三方项目。

## 目标插件类型

当前规划中的 crawler Source Plugin 可按能力拆分为以下几类：

- 新闻抓取插件
- 股价 / 行情抓取插件
- 特定内容搜索插件
- 关注公司财报及相关信息抓取插件
- X / Twitter 账号推文抓取插件

这些插件都属于 `source` 插件类型，统一通过 `plugin.yaml` 注册，并放在 `plugins/sources/` 或后续的 `runtime/plugins/` Source 命名空间下。

## 插件开发者职责

插件开发者负责：

- 提供插件目录和 `plugin.yaml`
- 定义 `config.schema.json`
- 声明插件所需配置字段
- 实现插件自己的抓取、解析和标准化能力
- 返回平台约定的 source 输出结构
- 提供 README 和最小测试

插件开发者不负责：

- 配置保存
- 配置校验落库
- 插件启停
- 调度与频率控制
- 审计与权限控制
- `RawEvent` 入库
- 去重
- `SourceBinding`
- `Event Bus`
- 插件生命周期托管

## 配置契约

插件开发者只声明“需要什么配置”，不负责配置的来源和持久化。

典型字段包括：

- `url`
- `frequency`
- `headers`
- `filters`
- `keywords`
- `symbols`
- `accounts`
- `time_window`

这些字段应通过 `config.schema.json` 声明约束。用户后续通过控制台或 API 填写配置，平台负责：

- 按 schema 校验
- 保存配置
- 生成运行时可用的 DTO / `effective_config`
- 将配置绑定到具体插件实例或 `SourceBinding`

## 运行时平台职责

运行时平台负责：

- 读取并校验插件配置
- 保存配置与变更历史
- 启停插件
- 调度抓取任务
- 传入 DTO / `effective_config`
- 控制权限、审计、限流、重试和生命周期
- 接收插件输出并写入统一事件链路

平台不应要求插件自行处理：

- 数据库存储
- 去重策略
- SourceBinding 管理
- Event Bus 发布
- 权限校验
- 生命周期编排

## 插件运行时接口约定

插件运行时只消费平台传入的上下文与配置，只返回自身能力产物。

```text
validated config
  -> effective_config DTO
  -> plugin fetch / search / read
  -> platform source output
  -> core runtime handles persistence and routing
```

这意味着插件应该专注于：

- 根据配置抓取或查询内容
- 在插件内处理供应商差异
- 将结果转换为平台约定的 source 输出结构
- 在失败时返回清晰错误

不应在插件内自行扩展为：

- 全局任务调度器
- 数据持久化层
- 多插件协作编排器
- 核心 runtime 代理

## Reader Fallback 约定

对网页正文、新闻详情或外链内容读取，初版默认准备两类读取路径：

- `Readability`
- `Jina Reader`

用途：

- 当主抓取路径内容缺失或抽取效果不稳定时，作为兜底路径
- 在不同站点和文本结构下提供更稳健的正文抽取能力

约束：

- 这两类能力应作为插件内部可切换策略，或作为通用 reader source/tool 插件被其他 Source Plugin 复用
- 不要求每个插件都复制两套完全独立实现，但插件方案必须考虑两种读取路径
- 外部 reader 的使用应接受平台的权限、限流、超时和审计控制

## 第三方开源能力复用

允许在插件内部复用第三方开源项目，例如 `Fincept Terminal`，但必须满足以下边界：

- 第三方能力属于插件实现细节，不上升为核心系统耦合
- 核心系统不直接 import、调度或依赖第三方项目
- 第三方能力的配置仍通过插件 schema 暴露
- 第三方能力的失败、降级和替换应由插件层负责吸收

## 与后续 issue 的关系

本说明只收住 crawler Source Plugin 的职责边界，不直接替代后续单个插件 issue。

后续每个插件 issue 仍应单独说明：

- 当前插件的单一目标
- 所需配置字段
- 抓取来源
- DTO 产出
- 最小测试
- 是否需要 `Readability` / `Jina Reader` fallback
- 是否复用第三方开源能力

## 待确认问题

- `Readability` 和 `Jina Reader` 更适合作为插件内部策略，还是沉淀为可复用的官方 Source / Tool 插件
- 不同 source 类型的输出是否全部统一为单一 source 输出契约，还是允许在进入核心系统前保留轻量 source-specific DTO
