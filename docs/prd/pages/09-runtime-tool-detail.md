# 09. Tool Invocation 详情

## 页面定位

Tool Invocation 详情用于查看一次受控工具调用的摘要、权限、风险、输入输出摘要、错误和 trace。它是排障页，不是自由脚本执行器。

## 用户任务

- 查看工具调用状态和耗时。
- 理解工具来自 core 还是插件。
- 查看风险等级和是否需要人工确认。
- 查看脱敏输入输出摘要。
- 排查失败、超时、blocked 或权限问题。

## 必须展示

- invocation_id、event_id、agent_run_id。
- tool_id、tool_name、provider_plugin_id。
- risk_level。
- requires_human_approval。
- status。
- input_summary。
- output_summary。
- timeout_ms、retry_count、duration。
- error_code / error_message。
- trace_id / request_id。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| pending / running | 展示当前状态 |
| succeeded | 展示输出摘要 |
| failed | 展示错误摘要和 retry_count |
| timed_out | 展示 timeout_ms |
| blocked | 展示权限、风险或人工确认阻断原因 |

## 安全边界

- 不展示 secrets、token、完整工具配置参数或包含敏感业务逻辑的私有配置。
- 不展示完整请求体、响应体或完整网页快照。
- 输入输出只展示脱敏摘要；典型敏感项包括 API keys、OAuth tokens、完整策略 JSON、账户信息和内部规则配置。

## 非目标

- 不做 Tool 开发台。
- 不做自由脚本执行器。
- 不做参数 schema 编辑器。
