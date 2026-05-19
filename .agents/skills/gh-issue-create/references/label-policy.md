# Label 策略

本仓库当前没有 `.github/labels.yml` 真相源。使用 `scripts/sync_repo_labels.py` 内置的标准标签集同步远端。

## 最小标签集合

每个开发 issue 至少需要：

- 一个 `type:*`
- 一个 `priority:*`
- 一个 `status:*`

影响范围明确时补一个或多个 `area:*`。复杂度能判断时补一个 `complexity:*`。

## type

- `type:feature`：产品、API、Web、Agent、插件、运行时能力。
- `type:bug`：已有行为错误或回归。
- `type:docs`：只改文档、说明或规范。
- `type:test`：主要补验证、fixture 或测试基础设施。
- `type:chore`：仓库维护、脚手架、依赖或工具链。
- `type:refactor`：不改变外部行为的内部整理。
- `type:discussion`：用户明确要讨论型 issue 时才用。

## priority

- `priority:high`：阻塞当前 phase、多个后续 issue 或关键验证链路。
- `priority:medium`：默认值。
- `priority:low`：有价值但不在当前关键路径上。

## status

- `status:needs-review`：默认新建状态，需要维护者确认。
- `status:ready`：目标、非目标、验收、未决点和 OpenSpec 关系都清楚。
- `status:blocked`：被明确上游决策、依赖或权限卡住。
- `status:in-progress`：已有人接手。

## area

按主要写入边界选择，不要为了完整把所有 area 都挂上：

- `area:api`
- `area:web`
- `area:core`
- `area:agent`
- `area:plugin`
- `area:contracts`
- `area:worker`
- `area:scheduler`
- `area:docs`
- `area:infra`
- `area:openspec`

## complexity

- `complexity:small`：单 area，1-2 个清晰任务。
- `complexity:medium`：默认值，跨 1-2 个 area 或 3-5 个子任务。
- `complexity:large`：跨多个 area，需要明显协调或分阶段。
