# 16. 事件级审计时间线

## 页面定位

事件级审计时间线按 Event 回放建议生成、建议变更、重分析、审批动作和关键状态变化。它回答的问题是：这条建议为什么变成现在这样，谁在什么时候做过什么。

## 用户任务

- 回放事件从捕获到当前状态的关键过程。
- 查看建议生成和变更前后摘要。
- 查看 request_reanalysis 的原因和结果。
- 查看人工 approve / reject / amend。
- 追踪 trace_id、request_id 和关联运行过程。

## 主对象和真源

主对象是 Event，审计信息来自多个 append-only 记录。

| 信息 | 真源 |
| --- | --- |
| 事件状态变化 | event_state_transitions |
| 审计动作 | audit_logs |
| 建议变化 | DecisionResult / Approval audit 摘要 |
| 重分析 | AgentRun / ApprovalInput / audit_logs |
| 人工动作 | ApprovalInput / ApprovalDecision / audit_logs |

## 页面结构

```text
页面头
  -> 当前事件摘要
  -> 时间线筛选
  -> 时间线节点
  -> 关联运行与审批入口
```

## 节点类型

V1 至少支持：

- event.state_changed。
- industry.analysis.completed。
- analysis.scored。
- decision.created。
- approval.requested。
- approval.resolved。
- reanalysis.requested。
- runtime.error_recorded。

## 节点展示规则

每个节点必须展示：

- 时间。
- actor_type / actor_id 或系统组件。
- action。
- outcome。
- 摘要。
- trace_id 或 request_id，若可用。

建议变更节点必须展示：

- 变更前摘要。
- 变更后摘要。
- 变更原因。
- 分数变化摘要。

重分析节点必须展示：

- 发起者。
- 发起原因。
- 是否改变建议。
- 关联 AgentRun。

人工动作节点必须展示：

- 操作者。
- 动作类型。
- 备注或原因。
- 修改前后摘要，若是 amend。

## 状态与失败路径

| 状态 | 页面行为 |
| --- | --- |
| 无审计记录 | 展示事件存在但暂无审计记录 |
| 只有系统节点 | 可按系统节点回放 |
| 只有人工节点 | 可按人工动作回放 |
| 部分节点缺 trace | 展示可用摘要，不阻断时间线 |
| 读取失败 | 展示错误摘要和重试 |

## 安全边界

- 不展示完整 chain-of-thought。
- 不展示 secret、token、完整私有策略、完整敏感 payload。
- before_state / after_state 只展示脱敏摘要。
- 审计记录只读，不允许在本页编辑历史。

## 验收口径

必须成立：

- 用户能按事件回放建议如何生成和变化。
- 用户能看到重分析是否改变建议。
- 用户能看到谁批准、拒绝或修改了建议。
- 用户能从时间线跳转到相关审批或运行详情。

失败信号：

- 审计页退化成无主线日志列表。
- 只能看到当前建议，看不到历史变化。
- 建议变化没有前后对比。

## 非目标

- 不做全局审计报表。
- 不做数据库日志浏览器。
- 不做不可篡改审计存证设计。
- 不做完整 payload diff 工具。
