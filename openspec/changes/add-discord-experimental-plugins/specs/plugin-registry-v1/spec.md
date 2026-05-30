## ADDED Requirements

### Requirement: 官方 Discord 实验插件是 Registry V1 的单插件样板

Plugin Registry V1 SHALL 允许第一版官方 Discord 实验插件以单个 manifest 和单个 config schema 的方式进入系统，而不需要新增核心注册机制。

#### Scenario: 单个官方 Discord 插件遵循既有 Registry V1 规则
- **WHEN** Registry 扫描第一版官方 Discord 插件
- **THEN** 该插件通过一个 `plugin.yaml` 作为登记真源
- **AND** 它必须满足 Registry V1 既有的 manifest 与 config schema 校验要求
- **AND** Registry 不需要为 Discord 插件新增硬编码注册逻辑

#### Scenario: Discord 官方插件作为新的官方样板而非新的协议入口
- **WHEN** 开发者参考第一版 Discord 官方实验插件实现新的官方或私有插件
- **THEN** 他们复用现有 Registry V1 协议入口
- **AND** 不会因为 Discord 插件而引入第二套 manifest、第二套 schema 或绕过 Registry 的发现方式

#### Scenario: 非法 Discord 插件只影响局部记录
- **WHEN** 第一版官方 Discord 插件的 manifest 或 config schema 非法
- **THEN** Registry 只把对应插件标记为 `invalid` 并返回 `last_error`
- **AND** 其他合法插件仍然可以被扫描和返回
- **AND** Registry 不会因为单个 Discord 插件非法而整体失败
