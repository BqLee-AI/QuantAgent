## 背景

当前仓库已有插件系统的方向性设计，但实现层仍处在骨架期：官方插件目录和 runtime 插件目录已存在，一个 placeholder source manifest 已存在，`packages/plugin-sdk` 仍是预留 package，API 和前端只有插件管理占位。V1 需要先建立可验证的登记处，而不是直接进入动态加载、热重载、自动安装依赖或交易执行。

## 目标与非目标

**目标：**

- 以 `plugin.yaml` 为 V1 插件真源，扫描 `plugins/` 与 `runtime/plugins/`。
- 校验 manifest 必填字段、插件 ID、版本、类型、capabilities 和 config schema 路径。
- 将插件扫描结果表示为结构化 `PluginRecord`，并保留 `last_error` 诊断信息。
- 单个插件非法时只标记该插件为 `invalid` 或 `failed`，不影响其他插件被发现。
- 暴露最小插件管理 API：列表、详情、配置 schema 查询、重新扫描。
- 保证 V1 不 import 插件 entrypoint、不自动安装依赖、不执行交易动作。
- 明确插件协议归 QuantAgent 管理，后续插件实现必须服从 Registry、SDK、ToolRegistry、Policy Gate 和审计边界。
- 给出从 V1 登记处演进到完整插件体系的路线，避免后续实现只停留在插件列表页。
- 为 V1.1 的最小插件 demo 预留验收边界，帮助插件作者理解完整流程但不扩大本轮实现范围。

**非目标：**

- 不实现插件市场、Git URL 安装、本地 zip 安装或 Python 依赖自动安装。
- 不实现生产热重载、动态代码隔离、多版本插件求解或 entry point discovery。
- 不实现完整 `packages/plugin-sdk`、ToolRegistry、Skill Registry、Agent workflow 或 SourceBinding 调度。
- 不实现真实 `broker.execute`、broker adapter、交易下单或高风险动作放行。
- 不实现插件自定义前端或 schema-driven 配置表单 UI。

## 决策

### 1. 采用 manifest-first，而不是 Python entry points first

V1 Registry SHALL 以 `plugin.yaml` 作为唯一插件登记真源，先扫描 `plugins/` 和 `runtime/plugins/`。`entrypoint` 字段在 V1 中只作为 manifest 元数据校验，不触发 import。

替代方案是使用 `importlib.metadata` entry points 发现插件。该方案适合成熟 Python 插件生态，但当前项目已经把官方插件、runtime 插件和管理 UI 都围绕 `plugin.yaml` 设计；过早引入 entry points 会弱化 manifest 真源，因此不采用为 V1 主路径。

### 2. Registry 落在 core，API 保持薄

Registry 模型、扫描器和错误结构 SHOULD 落在 `packages/core/src/quantagent/core/registry/`。API route 只负责权限、DTO、响应 envelope、HTTP 错误映射和调用 core Registry。

替代方案是把扫描逻辑写入 `apps/api` route。该方案会让 worker、scheduler 和后续插件管理复用困难，并违反 API 层不承载核心领域逻辑的边界，因此不采用。

### 3. V1 只做登记状态，不做运行状态

V1 插件状态 SHALL 限定为 `discovered`、`valid`、`invalid`、`enabled`、`disabled`、`failed`。其中 `enabled/disabled` 表示管理配置状态，不表示插件代码已经 import、load、start 或 subscribe。

替代方案是直接实现完整 `installed -> loaded -> started -> reloaded -> stopped -> uninstalled` 状态机。该方案依赖实例化、生命周期、资源释放和审计持久化，超出 V1 登记处范围，因此推迟。

### 4. 使用 `broker` 命名交易通道插件

V1 canonical plugin type SHOULD 使用 `broker` 表达交易通道插件。为了兼容历史文档和可能的旧 manifest，Registry MAY 接受 `executor` 与 `trade_executor` 作为输入别名，但 API 和内部规范输出 SHOULD 使用 `broker`。

替代方案是继续使用裸 `executor` 或 `trade_executor`。`executor` 容易与 Python/worker/scheduler 的任务执行器混淆，`trade_executor` 仍然强调“执行”而不是“交易通道”，也容易让真实执行看起来像默认能力，因此不作为 canonical type。

### 5. 失败可诊断，但不能扩大 blast radius

Registry 扫描 SHALL 捕获 YAML 解析、字段校验、未知类型、schema 文件缺失、重复 ID 等错误，并在对应 `PluginRecord.last_error` 中返回结构化摘要。单个插件失败不能让整个扫描 API 返回 500。

替代方案是遇到非法插件直接中断扫描。该方案会让一个 runtime 私有插件破坏官方插件可见性，因此不采用。

### 6. 插件协议由 QuantAgent 管理

V1 不只是在目录里寻找文件，而是在建立后续插件体系的协议入口。QuantAgent 应统一管理以下协议面：

- `plugin.yaml` manifest 字段、类型、capabilities、permissions、dependencies 和 `config_schema`。
- `config.schema.json` 的运行时校验规则，以及后续前端 schema-driven 表单的输入约束。
- 生命周期接口，例如 `load`、`start`、`stop`、`reload` 和 `health_check`，但 V1 只登记不执行。
- 插件暴露 tool/action 的方式，后续必须经过 ToolRegistry、capability、risk level、Policy Gate 和 audit。
- 插件错误结构，例如 code、message、stage、retryable、details 和 plugin id/version。

替代方案是让每个插件自行定义配置、生命周期和 tool 暴露方式。该方案会让插件生态很快失控，也会破坏审计、权限和前端管理能力，因此不采用。

### 7. V1 是完整插件流程的第一段，不是终点

完整插件流程应按阶段演进：

```text
发现 manifest
  -> 校验 manifest/config schema
  -> 记录 Registry 状态
  -> 配置 enable/disable
  -> 创建受控 RuntimeContext
  -> load/start/health_check
  -> 注册 tools/actions/source bindings
  -> 由 Scheduler / AgentRuntime / ToolRegistry 调用
  -> Decision / Policy Gate
  -> dry-run 或通知等低风险输出
  -> Persistence / Audit
```

V1 只覆盖前四步中的只读和管理状态部分；V1.1 才用一个最小 pull source demo 串起 manifest、config schema、受控入口和 RawEvent/mock 输出；真实交易执行继续推迟到 Policy Gate、审批和审计稳定之后。

### 8. 插件小 demo 是后续验收资产

V1.1 SHOULD 提供一个最小官方 demo 插件，优先使用 `source` 类型，例如 `quantagent.official.source.demo` 或扩展现有 placeholder。demo 插件应包含：

- `plugin.yaml`，覆盖 V1 规定的必填字段和 canonical type。
- `config.schema.json`，展示配置校验和默认配置边界。
- 一个最小 Python entrypoint，用于后续生命周期实现阶段证明 `load`、`health_check` 或 `fetch` 如何被宿主调用。
- 测试 fixture，证明 Registry 不需要硬编码插件 class、import 列表或 if/else。

该 demo 在 V1.1 之前只作为设计和验收要求，不在本 OpenSpec-only PR 中实现。

## 风险与取舍

- [风险] V1 不加载 entrypoint，用户可能误以为插件已经可执行。
  -> 缓解：API 状态和文档明确 `enabled` 不是 `loaded/started`，后续生命周期另开 change。

- [风险] `executor` / `trade_executor` 改名为 `broker` 可能与草案文档不一致。
  -> 缓解：V1 接受 `executor` / `trade_executor` alias，并在 PR 中说明这是对草案命名的收敛，不是实现真实交易。

- [风险] 不做持久化会让 enable/disable 状态暂时难以跨进程保留。
  -> 缓解：V1 只定义行为和最小 API；实现阶段可先用内存状态，后续配置持久化另开 change。

- [风险] 后续 agent 可能把 Registry 与 ToolRegistry、SourceBinding 一起做大。
  -> 缓解：tasks 明确拆阶段，OpenSpec-only PR 审核通过前不写实现。

- [风险] 只做 V1 登记处会让 reviewer 担心最终插件流程没有闭环。
  -> 缓解：design 和 spec 明确完整流程、协议归属和 V1.1 demo 验收，但 implementation tasks 仍然保持 V1 范围。
