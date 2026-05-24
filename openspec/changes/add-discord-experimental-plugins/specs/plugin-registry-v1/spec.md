## ADDED Requirements

### Requirement: 官方 Discord 实验插件是 Registry V1 的样板插件

Plugin Registry V1 SHALL 允许第一版官方 Discord 实验插件通过既有 `plugin.yaml` 和 `config.schema.json` 约束进入系统，而不需要新增核心注册机制。

#### Scenario: Discord 官方插件遵循既有 Registry V1 规则
- **WHEN** Registry 扫描第一版官方 Discord 发送与接收插件
- **THEN** 两个插件都通过 `plugin.yaml` 作为登记真源
- **AND** 两个插件都必须满足 Registry V1 既有的 manifest 与 config schema 校验要求
- **AND** Registry 不需要为 Discord 插件新增硬编码注册逻辑

#### Scenario: Discord 官方插件作为新的官方样板而非新的协议入口
- **WHEN** 开发者参考第一版 Discord 官方实验插件实现新的官方或私有插件
- **THEN** 他们复用现有 Registry V1 协议入口
- **AND** 不会因为 Discord 插件而引入第二套 manifest、第二套 schema 或绕过 Registry 的发现方式
