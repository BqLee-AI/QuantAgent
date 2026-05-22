# 03. 插件系统与 Registry 设计

## 文档状态

**状态**：草案 v0.1  
**范围**：插件类型、插件注册、manifest、Registry、依赖自动安装、热重载边界  
**不包含**：具体插件实现、插件市场、真实交易执行、安全签名系统

## 设计结论

- 初版固定五类插件：`source`、`industry`、`strategy`、`notification`、`executor`。
- 所有插件必须通过 `plugin.yaml` 注册。
- 禁止在核心代码中硬编码插件注册。
- 官方插件、第三方插件、社区插件、私有插件统一走 Registry。
- 初版支持插件热重载，但只保证开发环境和后台管理场景可用，不承诺生产环境零中断。
- 插件依赖支持自动安装。
- 插件必须声明版本。

## 插件类型

| 类型 | 职责 | 示例 |
| --- | --- | --- |
| `source` | 采集或接收外部信息 | RSS、URL watcher、X API、Readability/Jina link reader |
| `industry` | 对事件进行行业分析 | Oil、Semiconductor、Memory |
| `strategy` | 将分析结果映射为策略建议 | 趋势策略、事件冲击策略、期权策略 |
| `notification` | 发送通知或展示提醒 | UI、Discord、Telegram、Email |
| `executor` | 交易执行能力；初版只做虚盘，不操作实盘；协议仍使用 `dry_run` 命名 | Mock executor；美股券商、Binance、OKX 作为后续实盘候选 |

## 插件目录来源

```text
plugins/
  sources/
  industries/
  strategies/
  notifications/
  executors/

runtime/
  plugins/
```

目录约定：

- `plugins/` 存放官方出厂自带插件，可以进入 Git。
- `runtime/plugins/` 存放运行时安装的第三方、社区或私有插件，默认不进入 Git。
- Registry 同时扫描官方插件目录和运行时插件目录。
- 私有交易策略、敏感数据源关键词、未公开行业逻辑不应放入官方插件目录。

## 插件注册原则

插件只能通过 `plugin.yaml` 注册。核心代码不得通过 import 列表、if/else、硬编码 class name 等方式注册插件。

原因：

- 保证官方插件和第三方插件路径一致。
- 支持运行时安装、卸载、启停和热重载。
- 支持后台管理 UI 展示插件元信息。
- 支持后续插件市场或私有插件仓库。
- 避免每新增插件都修改核心代码。

## 插件 manifest

每个插件根目录必须包含 `plugin.yaml`。

```text
my_plugin/
  plugin.yaml
  src/
  config.schema.ts
  config.schema.json
  README.md
  tests/
```

### 最小字段

```yaml
id: quantagent.official.source.rss
name: RSS Source
type: source
version: 0.1.0
entrypoint: rss_plugin:plugin
description: RSS feed source plugin.
capabilities:
  - source.fetch
config_schema: config.schema.json
```

### 完整字段建议

```yaml
id: quantagent.official.industry.oil
name: Oil Industry Package
type: industry
version: 0.1.0
entrypoint: oil_plugin:plugin
description: Oil market event analysis package.
author: QuantAgent
homepage: https://github.com/BqLee-AI/QuantAgent
license: Apache-2.0

capabilities:
  - industry.analysis
  - industry.scoring
  - strategy.mapping

permissions:
  - network
  - market_data

dependencies:
  plugins:
    - id: quantagent.official.source.rss
      version: ">=0.1.0"
    - id: quantagent.official.source.x_api
      version: ">=0.1.0"
  python:
    - feedparser>=6.0.0

config_schema: config.schema.json
```

## 插件 ID 与命名空间

| 来源 | 命名空间示例 |
| --- | --- |
| 官方插件 | `quantagent.official.source.rss` |
| 社区插件 | `community.<author>.<plugin>` |
| 私有插件 | `private.<org>.<plugin>` |
| 本地实验插件 | `local.<name>` |

约束：

- 插件 ID 全局唯一。
- 同一插件 ID 可以有多个版本，但同一运行时只能启用一个版本。
- 官方插件必须使用 `quantagent.official.*`。
- 私有插件不得伪装成官方命名空间。

## Registry 职责

Registry 是插件系统的中心索引，但不直接承载业务逻辑。

职责：

- 扫描插件目录。
- 读取 `plugin.yaml`。
- 校验 manifest。
- 校验配置 schema。
- 维护插件状态。
- 解析插件依赖。
- 自动安装缺失依赖。
- 创建插件实例。
- 管理插件生命周期。
- 对外提供插件查询 API。

不负责：

- 直接执行行业分析。
- 直接执行交易。
- 直接抓取外部数据。
- 绕过插件接口调用具体实现。

## Registry 数据模型

```text
PluginRecord
  id
  type
  name
  version
  source
  path
  status
  manifest
  config_schema
  installed_at
  updated_at
  enabled_at
  disabled_at
  last_error
```

### 插件状态

```text
discovered
  -> validated
  -> installed
  -> configured
  -> loaded
  -> started
  -> stopped
  -> reloaded
  -> disabled
  -> uninstalled
  -> failed
```

## 插件生命周期

### 安装

```text
Install request
  -> Resolve source
  -> Download / Copy plugin
  -> Read plugin.yaml
  -> Validate manifest
  -> Resolve dependencies
  -> Auto install dependencies
  -> Validate config schema
  -> Register plugin
  -> Mark installed
```

### 启用

```text
Enable request
  -> Check installed
  -> Check dependencies
  -> Validate config
  -> Create instance
  -> Start plugin
  -> Subscribe topics
  -> Mark started
```

### 停用

```text
Disable request
  -> Stop plugin
  -> Unsubscribe topics
  -> Release resources
  -> Mark disabled
```

### 卸载

```text
Uninstall request
  -> Stop plugin if running
  -> Check reverse dependencies
  -> Remove runtime files
  -> Mark uninstalled
```

卸载不得删除历史事件、分析结果、审计记录和用户确认记录。

## 依赖自动安装

初版支持插件依赖自动安装。

### 依赖类型

| 类型 | 说明 |
| --- | --- |
| `plugins` | 依赖其他 QuantAgent 插件 |
| `python` | 依赖 Python 包 |
| `system` | 依赖系统能力，初版只检查不安装 |

### 自动安装策略

- 缺失插件依赖时，Registry 尝试从已配置插件源安装。
- 缺失 Python 依赖时，Registry 通过受控安装流程安装到插件运行环境。
- 缺失 system 依赖时，只提示用户，不自动安装。
- 自动安装必须记录日志。
- 自动安装失败时，当前插件进入 `failed` 或 `installed_but_blocked` 状态。

### 插件源

初版支持：

- Git URL。
- 本地 zip。
- 私有目录。

暂缓：

- 公开插件市场。
- 签名校验。
- 来源白名单。
- 复杂依赖冲突求解。

## Factory 与实例化

Factory 根据 manifest、配置和运行时上下文创建插件实例。

```text
Manifest + Config + RuntimeContext
  -> PluginFactory
  -> PluginInstance
```

Factory 规则：

- 不允许插件绕过 SDK 直接访问核心内部对象。
- 插件实例只能通过 RuntimeContext 获取 logger、event bus、storage、config、secrets。
- 插件实例化失败必须返回结构化错误。
- 同一个插件 ID 同一时间只允许一个 active instance。

## 插件接口

### 基础接口

所有插件都应支持：

```text
load(context)
start()
stop()
reload(config)
health_check()
```

### Source Plugin

```text
fetch()
subscribe()
normalize(raw_input)
```

### Industry Plugin

```text
analyze(event, context)
score(analysis)
map_to_markets(analysis)
```

### Strategy Plugin

```text
generate_actions(scored_analysis)
validate_action(action)
```

### Notification Plugin

```text
send(notification)
```

### Executor Plugin

```text
dry_run(action)
execute(action)
```

初版 executor 必须默认禁用真实 `execute`，只允许 `dry_run` 或 mock。

## 热重载边界

初版支持插件热重载，但只保证开发环境和后台管理场景可用，不承诺生产环境零中断。

热重载流程：

```text
Reload request
  -> Stop plugin
  -> Reload manifest/config/code
  -> Recreate instance
  -> Start plugin
  -> Health check
```

约束：

- 热重载失败时，插件进入 failed 或恢复旧实例。
- 正在处理中的事件不保证无损迁移。
- 生产环境如需零中断，需要后续设计滚动重启或多实例隔离。

## 配置 Schema

插件配置采用 `Zod authoring + JSON Schema runtime validation`。

```text
config.schema.ts
  -> config.schema.json
  -> Python runtime validation
  -> Schema-driven UI form
```

约束：

- 初版前端只支持 schema 驱动表单。
- 不支持插件自定义前端扩展。
- 官方插件必须提交 `config.schema.ts` 和 `config.schema.json`。
- 第三方插件可以只提交 `config.schema.json`，但开发体验会降级。

## 错误处理

```text
PluginError
  code
  message
  plugin_id
  plugin_version
  stage
  retryable
  details
```

常见错误：

- manifest 缺失。
- manifest 不合法。
- 插件 ID 冲突。
- 依赖安装失败。
- 配置校验失败。
- entrypoint 加载失败。
- health check 失败。
- 热重载失败。

## 审计要求

以下动作必须记录：

- 插件安装。
- 插件升级。
- 插件降级。
- 插件启用。
- 插件停用。
- 插件卸载。
- 插件热重载。
- 插件配置变更。
- 依赖自动安装。
- 插件执行错误。

## 初版实现范围

必须实现：

- `plugin.yaml` manifest 规范。
- 固定五类插件。
- Registry 扫描官方和 runtime 插件目录。
- manifest 校验。
- 插件版本记录。
- 插件启停。
- 插件热重载。
- 插件依赖自动安装。
- 插件配置 JSON Schema 校验。
- 基础插件 SDK 接口。

暂缓实现：

- 插件市场。
- 插件签名校验。
- 来源白名单。
- 复杂依赖冲突求解。
- 生产零中断热重载。
- 插件自定义前端扩展。

## 待确认问题

暂无。后续进入插件 SDK 代码设计或具体插件实现时再拆分讨论。
