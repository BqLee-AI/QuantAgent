# 08. Agent Run 详情

## 页面定位

Agent Run 详情用于展示一次 AgentRuntime 运行的结构化过程摘要。它帮助用户理解事件分析经过了哪些步骤、用了哪些 Skill 和 Tool、哪里失败或输出无效。

## 用户任务

- 查看 run 状态、耗时、输入摘要和输出摘要。
- 查看结构化 timeline。
- 查看使用的 AgentDefinition、Skill 和 Tool。
- 查看 provider_policy、model_used、token usage 和 cost estimate 摘要。
- 跳转到 Tool Invocation 详情。
- 跳转到 Model Providers / LLM Policies 排查模型供应商或 policy 问题。
- 通过 trace_id 关联事件、审批和审计。

## 必须展示

- run_id、event_id、run_type、status。
- AgentDefinition ID 和版本。
- started_at、ended_at、duration。
- input_summary 和 structured_output 摘要。
- provider_policy。
- model_used。
- token_usage。
- cost_estimate。
- timeline steps。
- used skills 摘要。
- tool invocations 摘要。
- provider / fallback 失败摘要，如果存在。
- error_code / error_message。
- trace_id / request_id。

## Timeline 规则

只展示结构化步骤摘要：

- Router 完成。
- IndustryAgent 启动。
- 调用 NewsVerificationTool。
- 输出结构化分析。
- schema validation 结果。

不展示完整模型推理链、完整 prompt 或完整 provider 原始响应。

## 模型与成本摘要

必须展示：

- 使用的 provider_policy。
- 实际 model_used。
- token_usage。
- cost_estimate。
- 是否触发 fallback。
- provider 错误或限流摘要。
- 进入 `/models` 对应 policy 或 provider 的链接。

这些信息只用于解释、排障和成本治理，不作为交易建议评分依据。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| running | timeline 可增量更新 |
| succeeded | 展示输出摘要 |
| failed | 展示失败步骤和错误摘要 |
| timed_out | 展示超时配置和已完成步骤 |
| output_invalid | 展示 schema 校验失败摘要 |

## 安全边界

- Skill 只展示 ID、来源、版本和授权摘要。
- Tool 只展示调用摘要，详情跳转到 Tool Invocation。
- 不展示 secret、prompt、完整私有策略或敏感参数。
- 不展示完整 provider 请求体、响应体或推理链。

## 非目标

- 不做模型调试器。
- 不做完整 CoT 查看器。
- 不做 AgentDefinition 编辑器。
