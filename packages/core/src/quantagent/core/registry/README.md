# Registry

`quantagent.core.registry` 负责插件发现、manifest 校验和 Plugin Detail 只读快照组装。

- 放这里：扫描插件目录、读取 `plugin.yaml`、校验 `config_schema`、组装 detail summary、推导受控依赖视图。
- 不放这里：FastAPI router、HTTP envelope、前端页面状态、Runtime Inspect 全局诊断、SourceBinding / SchedulerRun 读写模型、插件动作 mutation。

Plugin Detail V1 的边界：

- `list / rescan` 仍然围绕 registry 记录视图。
- `detail / config / dependencies / health / audit` 在这里组装只读快照，但只暴露插件中心 summary。
- `runtime inspect`、`SourceBinding`、`SchedulerRun` 继续走各自资源边界，不在这里混成第二套对象。
