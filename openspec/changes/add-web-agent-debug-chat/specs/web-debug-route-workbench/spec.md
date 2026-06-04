## MODIFIED Requirements

### Requirement: Fixed First-Batch Debug Subroutes
`/debug` 首批 SHALL 固定提供 `page-states`、`runtime-config`、`error-fallback`、`route-playground`、`plugin-config-form`、`agent-run-chat` 六个子路由。

#### Scenario: All first-batch routes exist in development
- **WHEN** 开发者在 development 环境检查 `/debug` 工作台
- **THEN** `/debug/page-states`、`/debug/runtime-config`、`/debug/error-fallback`、`/debug/route-playground`、`/debug/plugin-config-form`、`/debug/agent-run-chat` 都可访问
- **AND** `/debug` 根页展示插件配置表单调试入口、Agent Debug Chat 调试入口和用途说明
