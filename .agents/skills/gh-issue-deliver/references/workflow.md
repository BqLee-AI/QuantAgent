# gh-issue-deliver 工作清单

## 1. Plan 模式门槛

开始前先确认：

- 当前处于 Plan 模式。
- 当前环境支持结构化提问。
- 用户明确要接手或交付 GitHub issue。

如果不满足：

- 停下并要求切到 Plan 模式。
- 不要用普通聊天问题替代结构化提问。
- 不要提前实现。

进入实现前必须至少完成一轮结构化提问。即使 issue 已经清楚，也要确认本轮范围、非目标和实现前是否需要审核。

## 2. Issue 收敛

先读取 issue 和评论，并确认：

- 单一问题是什么
- 为什么现在做
- 明确不做什么
- 成功、失败和非成功信号是什么
- 是否已有 OpenSpec change

如果 issue 边界不清，先问 1-3 个问题。问题必须影响实现路径或验收边界。

如果评论里有后续约束、维护者确认、AI review 摘要或失败日志，必须纳入问题定义。issue 正文不是唯一真源。

## 3. OpenSpec 判断

需要 OpenSpec 的情况：

- 外部行为变化
- 架构或 package 边界变化
- API、WebSocket、前后端契约、插件契约、Agent workflow 或数据库 schema 变化
- 影响多文件约定或后续 issue 依赖

通常不需要 OpenSpec 的情况：

- 拼写、链接、注释或局部文案修复
- 不改变行为的小范围测试修复
- 明确不影响契约的仓库维护

不确定时按需要 OpenSpec 处理。

## 4. Artifacts 要求

实现前至少确认这些内容存在并一致：

- `proposal.md`：背景、目标、非目标、验收摘要
- `tasks.md`：任务依赖、输入输出、写入边界、验证任务
- `specs/**/spec.md`：外部行为和场景
- `design.md`：只有当实现选择、风险或替代方案需要记录时才需要

不要把聊天摘要当成 spec artifact。

新建或大幅更新 artifacts 后，不允许直接进入实现。必须先提 OpenSpec-only PR，并等待维护者在 PR 下明确评论“没问题”或批准。

## 5. 审核点

需要先暂停给用户审核的情况：

- 新建或大幅改写 OpenSpec change
- issue 的目标、非目标或验收口径发生变化
- 实现发现原设计不成立
- 需要引入新的 package、依赖、数据模型或执行路径

如果 issue 已有关联且清晰的 active change，也要确认维护者已经在对应 OpenSpec PR 下明确认可，或该 change 已合入。仅本地 artifacts 不能作为实现依据。

OpenSpec-only PR 要求：

- 只包含本 change 的 proposal、design、specs、tasks 和必要说明。
- 先运行 `openspec validate <change-id> --type change --strict --json`。
- 维护者明确评论“没问题”或批准前，不实现代码、不加依赖、不改运行时代码。
- 获得明确认可后即可基于 OpenSpec PR 分支或当前工作分支进入实现分支，不必等待合入。

需要提醒用户沉淀的情况：

- 发现规则会反复影响后续 AI 开发。
- 发现设计文档和实现长期边界不一致。
- 发现多个 issue 都在重复同一类未决点。
- 发现新 package 或依赖方向需要仓库级约束。

## 6. 实现顺序

优先处理关键路径：

1. 契约和边界
2. 最小实现
3. 测试或 harness
4. 文档和任务状态
5. 最终验证

并行任务只能在写入边界不冲突时拆分。当前环境没有明确委派许可时，在本线程完成。

## 7. 验证原则

验证按风险选择：

- OpenSpec artifact 改动后跑 `openspec validate`
- API route、envelope、OpenAPI、readiness 改动后跑 API unittest
- Web 纯逻辑跑 Vitest
- 页面路由或浏览器行为跑 Playwright E2E
- 组件浏览器行为跑 Playwright CT
- 前端结构性改动至少跑 lint/build 或说明跳过原因

不要把生产服务、真实密钥、外部数据源或 live trading 写成默认验证。

## 8. AI Review 判断

PR 或 issue 中的 AI review 只是一种输入，不是裁判：

- 先判断它指向的文件、行号和代码是否仍然存在。
- 再判断它是否符合当前依赖版本和项目规则。
- 再判断它描述的是 bug、风格偏好、过度泛化还是旧版本误判。
- 正确的 finding 要修或明确记录后续 issue。
- 不正确的 finding 要回复证据，不要沉默忽略。
- 不确定时做最小验证或查官方文档，不要凭模型记忆互相覆盖。
