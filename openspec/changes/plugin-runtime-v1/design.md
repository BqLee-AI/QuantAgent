## 背景

Registry V1 已经明确：`plugin.yaml` 是插件登记真源，V1 不 import、不实例化、不执行 manifest 中的 `entrypoint`。Issue #140 需要推进下一层：在不扩大到调度、事件链路、依赖安装或真实执行的前提下，让插件可以被平台统一加载、配置注入、生命周期托管和调用。

Runtime V1 的核心风险不是“能不能 import 一个对象”，而是边界是否收住：插件不能自行读取数据库、持有 ORM session、启动长期后台循环、绕过宿主调度、绕过 ToolRegistry/Policy Gate 或各自定义错误协议。与此同时，插件作者需要一个稳定而轻量的 SDK surface，否则每个插件都会复制样板。

## 目标与非目标

**目标：**

- 复用 Registry V1 的有效插件记录和 manifest entrypoint 作为 runtime 加载入口。
- 定义平台侧 Runtime 如何加载插件 entrypoint，并在失败时返回结构化错误。
- 定义 `RuntimeContext` 的最小受控内容，避免插件直接依赖 core 内部服务、数据库或调度器。
- 定义配置注入方式：平台将已校验的 JSON / DTO / `effective_config` 传入插件，插件不自行读取用户输入、数据库或环境中的业务配置。
- 定义生命周期 hook：`load`、`start`、`stop`、`health_check`。
- 定义统一调用入口：插件接收标准 request DTO，返回标准 result DTO 或结构化错误。
- 定义 `packages/plugin-sdk` 的最小协议与可选轻量基类边界。
- 定义 Runtime V1 行为测试或 contract test 的最小 harness。

**非目标：**

- 不实现插件市场、远程 Git / zip 安装、依赖自动安装或插件隔离环境。
- 不实现 SourceBinding、Scheduler loop、RawEvent 入库、Event Bus 发布或行业分析链路。
- 不实现真实 executor execute、broker adapter、live trading 或高风险动作放行。
- 不把 API router 变成插件加载器或 runtime 领域逻辑承载处。
- 不设计完整 Plugin SDK、完整工具注册系统、Skill Registry 或 AgentRuntime。
- 不允许插件直接访问 DB session、ORM model、内部 service、scheduler 或自定义前端组件。

## 决策

### 1. Runtime V1 复用 Registry V1，不重新发现插件

Plugin Runtime V1 SHALL 从 Registry 返回的有效 `PluginRecord` 出发，读取 manifest 中的 `entrypoint`、`id`、`version`、`type`、`capabilities` 和 `config_schema` 等信息。Runtime 不扫描额外目录，也不通过硬编码 class、import 列表或 if/else 注册插件。V1 的 entrypoint 必须是插件 class 或 factory，每次运行时调用都创建新的插件实例；Runtime 不接受预实例化 singleton 对象作为 entrypoint，以避免并发请求覆盖同一个 RuntimeContext。

替代方案是在 Runtime 中再次扫描插件目录或维护独立插件列表。该方案会制造第二套插件真源，破坏 Registry V1 已经收住的 manifest-first 边界，因此不采用。

### 2. SDK 提供轻量基类，但 Runtime 以协议能力为准

`packages/plugin-sdk` SHOULD 提供可选轻量 `BasePlugin`，用于减少插件作者样板代码。`BasePlugin` 可以提供默认生命周期方法、保存 `RuntimeContext`、受控 logger 访问和错误转换辅助。

Plugin Runtime SHALL 不要求插件对象必须继承 `BasePlugin`。Runtime 应基于 manifest entrypoint 和 runtime protocol 判断插件是否具备所需生命周期与调用能力。换句话说，`BasePlugin` 是开发体验层，不是系统唯一识别机制。

替代方案是强制所有插件继承一个 concrete base class。该方案短期简单，但会让不同类型插件被过早绑定在一个大型继承层级上，也会让后续协议演进变得笨重，因此不作为 V1 的核心耦合点。

### 3. V1 先定义统一 invoke，类型专用能力后续增量扩展

Runtime V1 SHALL 定义统一 `invoke` 风格入口，用于表达“平台调用某个插件能力并获得结构化结果”。请求中应包含 capability、request id、输入 DTO 和必要元数据。不同插件类型后续可以在 SDK 中提供更窄的 typed helper，但 V1 不把每一种插件类型的方法全集一次性钉死。

替代方案是在 V1 中直接定义所有类型专用接口的完整方法签名。该方案会把本 change 扩大到多个业务链路，并迫使尚未稳定的 DTO 过早冻结，因此推迟。

### 4. RuntimeContext 是受控上下文，不是服务定位器

RuntimeContext SHOULD 只暴露插件运行所需的最小信息：

- `plugin_id`
- `plugin_version`
- `request_id`
- 受控 logger
- 已校验后的 config DTO / effective config
- 运行模式，例如 local、test、worker
- 必要的只读运行元数据

RuntimeContext SHALL NOT 默认暴露数据库 session、ORM model、内部 service、scheduler、Event Bus publisher、AgentRuntime、ToolRegistry 或任意 secret resolver。后续确需暴露宿主能力时，应通过明确的 port / adapter / capability 边界增量设计。

### 5. 配置由平台校验并注入，插件不自行寻找配置真源

Plugin Runtime SHALL 接收平台已经根据 `config.schema.json` 校验过的配置，并将其作为 DTO / JSON-like object 注入插件。插件不能自行读取用户输入、数据库配置记录或平台内部配置存储来决定业务行为。

插件可以读取普通运行环境变量用于非业务性运行参数，但不得把 secret、token 或用户业务配置绕过平台配置协议直接读入。

### 6. 生命周期由平台托管，插件不自行启动长期后台循环

Runtime V1 SHOULD 定义以下生命周期 hook：

```text
load(context)
start()
health_check()
stop()
```

生命周期调用顺序由 Runtime 负责。`load` 用于注入上下文和完成轻量初始化；`start` 用于进入可调用状态；`health_check` 用于返回健康状态；`stop` 用于释放插件自身资源。

插件 SHALL NOT 在 V1 中自行启动长期后台循环、未托管线程、独立 scheduler 或绕过平台治理的订阅。需要调度的能力应由后续 Scheduler / SourceBinding 设计接入。

### 7. 失败返回结构化错误，并按 stage 归因

Runtime V1 SHALL 将加载、生命周期和调用失败转换为结构化错误：

```text
PluginRuntimeError
  code
  message
  stage
  retryable
  details
```

建议的 `stage` 包括：

- `load`
- `config`
- `start`
- `invoke`
- `health_check`
- `stop`

错误信息 SHALL 适合 API、worker log 和审计记录复用，不暴露 secret、token、cookie、stack trace 原文或本地私有路径。底层异常可被记录为脱敏摘要。

### 8. 插件失败不应自动等同于 Registry 失效

单次 invoke 失败 SHOULD 默认记录为本次运行失败，不自动把插件 Registry 状态改为 `failed`。只有 entrypoint 持续不可加载、生命周期无法进入可用状态，或后续状态管理策略明确要求时，Runtime 才可以将插件运行状态标记为 failed。

这是为了区分“插件包不可运行”和“某次调用输入、外部服务或临时条件失败”。V1 应在错误记录中保留 stage、retryable 和 details，让后续状态管理策略有证据可用。

## 风险与取舍

- [风险] 提供 `BasePlugin` 后，实现者可能误以为必须强制继承。
  -> 缓解：spec 明确 Runtime 以协议能力为准，`BasePlugin` 只是 optional helper。

- [风险] 统一 `invoke` 过于抽象，后续 source、industry 等 typed 方法仍需要补充。
  -> 缓解：V1 先稳定运行时主干和 DTO 包装，typed helper 后续按真实插件类型增量添加。

- [风险] RuntimeContext 过瘦，插件实现者可能希望直接拿 DB 或 scheduler。
  -> 缓解：V1 明确这类能力不直接暴露；如确需访问，必须通过后续 port / adapter / capability 设计。

- [风险] 单次失败不更新 Registry 状态，用户可能看不到插件异常。
  -> 缓解：Runtime V1 需要返回结构化错误；后续可增加运行记录、审计或插件运行状态视图，但不把 Registry 登记状态和单次调用结果混为一谈。
