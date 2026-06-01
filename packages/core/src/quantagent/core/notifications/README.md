# `quantagent.core.notifications`

## 职责

这个目录承载通知插件 ingress 进入平台后的共享编排边界，当前只负责：

- 调用 `notification.receive`
- 生成平台侧 `receive fact`
- 追加 append-only 审计
- 把标准化输入移交给后续 approval handoff seam

## 不负责

- 不解析平台专属协议；这些逻辑留在具体 notification 插件里。
- 不直接发布 `approval.*` topic。
- 不直接实现完整审批状态机、Policy Gate 或 broker 执行。
- 不依赖 FastAPI、API envelope、具体插件实现或数据库 session。

## 目录说明

- `ingress.py`: notification ingress 平台编排入口
- `models.py`: receive fact / audit / approval handoff 的共享模型
- `repository.py`: receive fact repository seam 与内存实现
- `audit.py`: append-only 审计 sink seam 与内存实现
- `handoff.py`: approval handoff port 与默认 no-op / 内存实现

## 设计说明

`approval handoff` 在这里故意只做 seam，不做审批业务本身。原因是 notification ingress 只负责把外部渠道输入收成平台事实；真正的审批编排、topic 和状态机由更上层 approval change 负责。
