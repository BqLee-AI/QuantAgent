## 背景

Plugin Registry V1 已经收住了 `plugin.yaml` 扫描、manifest 校验、配置 schema 查询和结构化登记记录，但插件仍停留在“可发现、可展示、可诊断”的阶段。当前系统还没有统一的插件运行时契约：插件 entrypoint 如何加载、配置 DTO 如何注入、生命周期如何托管、调用入口如何统一、失败如何结构化返回，仍没有稳定边界。

如果在这个阶段直接推进具体插件实现，每个插件很容易自行定义基类、配置读取、错误格式和生命周期处理方式，导致插件作者承担本应属于插件底座的职责，也会让 core、API、worker 后续难以用同一条路径调用插件能力。

本 change 聚焦 Plugin Runtime V1：在 Registry V1 之上定义最小可运行插件底座，使平台能够通过统一路径加载插件、注入平台校验后的配置、托管生命周期、调用能力并返回结构化结果或错误。本 change 同时明确 `packages/plugin-sdk` 应提供轻量、可选的插件基类和协议类型，但 Runtime 以 manifest entrypoint 和协议能力为准，不把具体基类变成唯一识别机制。

## 改动

- 定义 Plugin Runtime V1 的主流程：从 Registry 的有效插件记录出发，加载 manifest `entrypoint`，创建受控 `RuntimeContext`，调用生命周期 hook，并通过统一入口执行插件能力。
- 定义 `packages/plugin-sdk` 的最小职责：提供插件作者可复用的 DTO、Protocol、结构化错误类型和可选轻量 `BasePlugin`。
- 定义 `BasePlugin` 的边界：它是开发体验层，提供默认生命周期行为、保存 context、访问受控 logger 和辅助错误转换；它不是 Runtime 唯一接受的插件类型。
- 定义 RuntimeContext 最小内容：`plugin_id`、`plugin_version`、`request_id`、受控 logger、平台校验后的 config DTO、运行模式和必要的只读运行上下文。
- 定义生命周期最小接口：`load`、`start`、`stop`、`health_check`，并明确 V1 不允许插件自行启动后台循环、长期线程或绕过宿主调度。
- 定义统一调用入口：插件接收 JSON-like / Pydantic-like request DTO，返回 JSON-like / Pydantic-like result DTO；Runtime 负责把插件异常转换为结构化错误。
- 定义结构化错误字段：`code`、`message`、`stage`、`retryable`、`details`，并要求脱敏，不暴露 secret、token、cookie、stack trace 原文或本地私有路径。
- 明确 V1 非目标：不实现插件市场、远程安装、依赖自动安装、SourceBinding、Scheduler loop、Event Bus 发布、RawEvent 入库、真实 executor execute 或 live trading。

## 能力

### 新增能力

- `plugin-runtime-v1`: 定义 QuantAgent 插件运行时 V1 的配置注入、生命周期、统一调用、SDK 基类/协议和结构化错误边界。

## 影响

- `packages/core/src/quantagent/core/runtime/**` 或等价 core runtime 落位：后续实现宿主侧插件加载、RuntimeContext 创建、生命周期调用、统一 invoke 和错误包装。
- `packages/plugin-sdk/**`：后续实现插件作者使用的 Protocol、DTO、`BasePlugin` 和错误辅助类型。
- `packages/core/src/quantagent/core/registry/**`：Runtime V1 复用 Registry V1 的 `PluginRecord`、manifest、entrypoint、status 和错误结构，不重新发明插件发现协议。
- `plugins/**` 与 `runtime/plugins/**`：后续插件 entrypoint 必须满足本 change 定义的 runtime 协议或使用 SDK 提供的轻量基类。
