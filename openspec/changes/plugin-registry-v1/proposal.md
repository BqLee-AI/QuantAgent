## 背景

QuantAgent 已经在 `docs/design/03-plugin-system-and-registry.md`、`plugins/`、`runtime/plugins/` 和 `packages/plugin-sdk/` 中预留插件系统边界，但当前代码还没有真正的 Plugin Registry、manifest 校验、插件查询 API 或最小生命周期状态。继续直接实现插件运行、依赖安装或交易执行会把风险边界提前拉满，也容易让后续 agent 绕过 `plugin.yaml` 真源。

本 change 先收敛插件系统 V1 的 OpenSpec 方案：第一版只建设 manifest-first 的插件登记处，证明系统能够发现、校验、展示和诊断插件；不加载插件 entrypoint，不自动安装依赖，不做热重载，不接真实交易执行。

## 改动

- 定义 `plugin.yaml` 作为 V1 插件登记真源，Registry 扫描官方插件目录 `plugins/` 与运行时插件目录 `runtime/plugins/`。
- 定义核心模型边界：`PluginManifest`、`PluginType`、`PluginStatus`、`PluginRecord`，并明确必填字段、类型别名和结构化错误。
- 定义 Registry 扫描器行为：单个插件失败不能导致整体扫描失败，重复 ID 标记冲突，不做版本求解。
- 定义插件管理 API 边界：列表、详情、配置 schema 查询和重新扫描，API 层只做 DTO、鉴权、响应 envelope 和路由接入。
- 定义最小状态集合：`discovered`、`valid`、`invalid`、`enabled`、`disabled`、`failed`。V1 的 enable/disable 只是配置状态，不等于 import、load 或 start。
- 将历史 `executor` 类型收敛为 `trade_executor` 的兼容别名策略：V1 可读入旧值，但规范输出使用 canonical type。
- 明确插件协议由 QuantAgent 管理：manifest、config schema、capabilities、生命周期、tool/action 暴露和错误结构都必须通过 Registry/SDK 契约演进，不由单个插件私自定义。
- 明确从 V1 登记处到最终插件体系的演进路线：V1 先做 Registry 与诊断，V1.1 再做最小 pull source demo，后续再接 RuntimeContext、ToolRegistry、Scheduler、AgentRuntime、Policy Gate 和 dry-run `trade_executor`。
- 明确后续 V1.1 需要提供一个可审查的小 demo 插件，用来证明第三方插件作者应该如何写 `plugin.yaml`、`config.schema.json` 和最小插件入口；demo 只走只读或 mock 路径，不接真实外部副作用。

## 能力

### 新增能力

- `plugin-registry-v1`: 定义 QuantAgent 插件 Registry V1 的 manifest-first 扫描、校验、状态、API 与非目标边界。

## 影响

- `packages/core/src/quantagent/core/registry/**`：后续实现 Plugin Registry、manifest 模型、扫描器和结构化错误的首选落位。
- `apps/api/src/quantagent/api/routers/**` 与 `apps/api/src/quantagent/api/schemas/**`：后续实现插件管理 API 的薄封装落位。
- `plugins/**` 与 `runtime/plugins/**`：作为 Registry V1 的扫描来源；官方插件和运行时插件走同一 manifest 入口。
- `plugins/sources/placeholder-source/**`：作为 V1 扫描与验收样例。
- `packages/plugin-sdk/**`：本 change 不要求实现完整 SDK，只保留后续从 Registry 反推的扩展位。
