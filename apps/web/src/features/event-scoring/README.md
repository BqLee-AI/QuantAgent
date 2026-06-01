# Event Scoring Feature

该目录承接事件评分体系与高价值事件判定的前端语义落点。

当前阶段负责：

- 评分相关的前端局部类型与 mock contract。
- 事件 / 审批页面共用的评分标签、说明文案和降级状态格式化。
- 重点事件卡片与审批卡片的评分摘要展示组件。

当前阶段不负责：

- 真实 API 请求与 TanStack Query 接入。
- route 入口、loader、search params 或应用级 runtime 初始化。
- 决策放行、审批 mutation、真实执行或权限策略。

后续进入正式 API 接入时，应优先在本目录继续补齐 `api/`、`queries/`、`hooks/`，而不是把评分字段和筛选逻辑继续堆回 `features/mainflow`。
