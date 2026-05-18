# AGENTS.md

## 定位

- `runtime` 是 QuantAgent 的本地运行时状态目录，不是业务源码目录。
- 这里承载本地安装插件、运行配置、缓存数据、日志和未来插件隔离依赖环境。
- `runtime` 对应 `docs/design/10-deployment-and-runtime-design.md` 中的运行时边界：代码可重建，运行时状态不可假装成源码。

## 目录边界

- `runtime/plugins` 存放第三方、社区、私有或用户运行时安装的插件；官方随代码分发插件放在 `plugins/`。
- `runtime/config` 只保存本地 override、bootstrap 配置或 secret reference，不保存应进入源码的默认配置。
- `runtime/data` 保存本地缓存、临时数据、导入导出和可重建运行数据。
- `runtime/logs` 保存本地排查日志、插件安装日志和运行时补充日志。
- 未来如果引入 `runtime/plugin-envs`，它只用于插件隔离依赖环境，不能污染主 Python runtime。

## 行为约束

- 不提交真实 secret、token、私有策略、私有插件、运行日志、缓存数据或插件隔离环境。
- 不把 `runtime/config` 当作配置真源；插件当前运行配置的长期真源应进入数据库或受控配置层。
- 不把 `runtime/plugins` 中的私有插件复制到 `plugins/`，除非 issue 或 PR 明确要求将其转为官方插件。
- 不在业务代码中依赖某个本地 runtime 文件必然存在；缺失时应清晰降级或报出可行动错误。
- 不随意删除 `runtime` 下的数据、插件或日志；清理前必须确认是本地临时产物，且不会破坏用户排查线索。
- 文档、PR 或测试需要 runtime 示例时，使用脱敏样例或 fixture，不引用本地真实内容。

## 架构约束

- 官方插件和运行时插件都应通过 Registry 进入系统，不能因为文件在 `runtime/plugins` 就绕过 manifest、配置校验和审计。
- 插件依赖自动安装必须可审计、可回滚或可重建；失败信息可以落日志，但不得输出 secret 原文。
- `runtime/logs` 是排查辅助，不是审计真源；关键状态变化仍应进入数据库或 append-only audit。
- 对 `runtime` 目录结构、配置分层或插件持久化边界的长期调整，需要回写设计文档或关联 OpenSpec 真源。
