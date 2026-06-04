## 1. 真源确认与依赖准备

- [ ] 1.1 回读 #284 issue 正文和评论，确认无新增约束或范围变化。
- [ ] 1.2 读取 `packages/agent/AGENTS.md`、`.agents/skills/references/engineering-quality-gate.md`、`.agents/skills/references/core-and-plugin-architecture-gate.md`、`docs/agent/02-planner-executor-architecture.md`、`docs/agent/05-tooling-and-output-contracts.md`、`docs/agent/08-run-scoped-context-tools.md`、`docs/agent/09-agent-artifact-ownership.md` 和 `docs/design/05-agent-workflow-design.md`。
- [ ] 1.3 实现前查阅官方 DeepAgents docs/examples、`https://docs.langchain.com/llms.txt` 索引和本地安装版本，记录关键 API 签名；文档上下文较长时安排 SubAgent 汇总。
- [ ] 1.4 检查 `packages/agent` 是否已纳入 Python workspace/test 配置；如未纳入，做最小配置更新。

## 2. Package 结构与契约

- [ ] 2.1 建立 `packages/agent/src/quantagent/agent/` 职责目录：`definitions/`、`runtime/`、`tools/`、`artifacts/`、`streaming/`、`testing/`。
- [ ] 2.2 新增 `packages/agent/README.md`，说明职责、入口、子目录、调用方式、不要放什么和 DeepAgents 复用边界。
- [ ] 2.3 实现 Pydantic strict models：`AgentDefinition`、`SubAgentDefinition`、`RuntimePolicy`、`ToolProfile`、`ToolBinding`、`AgentRunRequest`、`AgentRunResult`、`RunContextSnapshot`、`ToolRuntimeContext`、`ArtifactRef`、`AgentRunEvent`。
- [ ] 2.4 为契约添加单元测试，覆盖未知字段拒绝、ID-first 命名、敏感字段不进入 safe summary。

## 3. Artifact 与工具 Adapter

- [ ] 3.1 实现 `ArtifactStore` Protocol 和 `InMemoryArtifactStore`，支持 `put/get/list_for_run` 或等价最小接口。
- [ ] 3.2 实现 `ToolAdapter`，将平台工具包装成 DeepAgents 可调用工具，并注入 `ToolRuntimeContext`。
- [ ] 3.3 实现工具 started/completed/failed 摘要事件和错误脱敏包装，覆盖 timeout 或异常路径。
- [ ] 3.4 添加测试覆盖 artifact ID-first 返回、hidden context 注入、工具失败结构化事件和敏感信息不泄露。

## 4. Runtime 与 Streaming

- [ ] 4.1 实现 `AgentRuntime.run` 与 `AgentRuntime.run_stream`，内部使用当前版本验证可用的 `create_deep_agent()`。
- [ ] 4.2 接入 DeepAgents tools、subagents、backend、skills、checkpointer/interrupt policy 的 MVP 配置；延后能力以注释或 README 说明原因。
- [ ] 4.3 实现 `streaming/adapter.py`，将 DeepAgents/LangGraph chunk 映射为稳定 `AgentRunEvent`。
- [ ] 4.4 实现 run-level 错误处理，确保失败输出 `run.failed` 且不暴露 traceback、prompt、secret 或 provider raw response。
- [ ] 4.5 添加 fake model / fake tool harness，支持无外部 provider 的 runtime smoke test。

## 5. 验证与 CR

- [ ] 5.1 运行 `uv run pytest packages/agent/tests` 或实现后确定的最小等价命令。
- [ ] 5.2 运行 `git diff --check`。
- [ ] 5.3 安排 SubAgent CR，重点检查：是否重复造 DeepAgents 能力、是否出现大 State、是否越过 ToolAdapter/hidden context、是否泄露敏感内容、是否违反 package 依赖方向。
- [ ] 5.4 修复 CR finding 后再次运行相关测试。
- [ ] 5.5 PR 说明关联 #284 和本 change，列出 DeepAgents 官方文档/examples 查阅记录、采用的内置能力、验证结果、未验证风险和后续 issue 依赖。
