## ADDED Requirements

### Requirement: quantagent-demo CLI demonstrates the minimum plugin-to-consumer pipeline

系统 MUST 提供一个 `quantagent-demo` CLI，在不依赖 Kafka、数据库或外部服务的情况下，演示最小插件调度到事件消费闭环。

#### Scenario: CLI runs the full minimum pipeline

- **GIVEN** 开发者在本地仓库环境运行 `quantagent-demo`
- **WHEN** CLI 初始化最小演示环境
- **THEN** 它 MUST 扫描官方插件目录
- **AND** 它 MUST 触发一个官方 `source.fetch` 插件
- **AND** 它 MUST 发布 `source.event.captured`
- **AND** 它 MUST 让一个 fake consumer 实际收到该事件

### Requirement: CLI uses the real scheduling and runtime path

`quantagent-demo` MUST 通过当前正式的 Registry、Runtime 和 SchedulingService 路径驱动插件，而不是直接调用插件 helper。

#### Scenario: CLI triggers placeholder source through scheduling service

- **GIVEN** 仓库中存在 `quantagent.official.source.placeholder`
- **WHEN** CLI 运行 demo
- **THEN** 它 MUST 通过 Registry 发现该插件
- **AND** 它 MUST 通过 `PluginSchedulingService.trigger()` 触发 `source.fetch`
- **AND** 它 MUST NOT 直接 import 插件对象并绕过调度层

### Requirement: CLI uses InMemoryEventBus and a fake consumer

`quantagent-demo` MUST 使用 `InMemoryEventBus` 和单一 fake consumer，证明事件已经离开插件执行路径并到达下游订阅者。

#### Scenario: Fake consumer receives source.event.captured

- **GIVEN** `source.fetch` 成功执行并通过 bridge 发布事件
- **WHEN** `source.event.captured` 被发布
- **THEN** fake consumer MUST 实际收到该事件
- **AND** fake consumer MUST 至少打印 topic、event id 或 payload summary 中的一部分

### Requirement: CLI stays within the minimum demo boundary

`quantagent-demo` MUST 只证明最小 source 事件闭环，不扩展为业务主链演示。

#### Scenario: Demo does not continue into business orchestration

- **WHEN** CLI 成功收到 `source.event.captured`
- **THEN** 它 MUST NOT 在本轮继续触发 analysis、strategy、discord、approval 或 broker 节点
- **AND** 它 MUST NOT 依赖 Kafka、数据库、外部网络或额外 provider

### Requirement: CLI provides human-readable success and failure output

`quantagent-demo` MUST 以人类可读日志展示演示结果，并通过退出码表达成功或失败。

#### Scenario: Successful run prints the key stages

- **GIVEN** CLI 成功跑通 demo
- **WHEN** 命令结束
- **THEN** 输出 SHOULD 依次包含插件扫描、插件触发、事件发布和 fake consumer 收到事件四个阶段的可读提示
- **AND** 进程 MUST 以成功退出码结束

#### Scenario: Failed run exits non-zero with minimal error summary

- **GIVEN** Registry 扫描失败、插件触发失败或事件消费未发生
- **WHEN** CLI 结束
- **THEN** 输出 MUST 打印最小错误摘要
- **AND** 进程 MUST 以非零退出码结束
