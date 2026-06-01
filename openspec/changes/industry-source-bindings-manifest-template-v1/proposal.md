## 背景

`docs/design/07-industry-package-design.md` 已要求行业包通过 `source_bindings` 声明 source 依赖，并通过 `config_template` 指向默认模板；`docs/design/06-source-plugin-design.md` 又明确 pull source 的调度主对象是 `SourceBinding`，不是裸 source plugin。当前仓库已经有 RSS Source Plugin V1（#148）、`SourceBinding Template / Effective Config` 契约（#215）和 `SourceBinding / SchedulerRun` 持久化（#216）等前置议题，但行业包这一侧仍缺少一份可审查的目录与样例约定。

如果这一层不先收住，后续行业包实现很容易把 binding 模板散落在任意 YAML、README 或代码常量中，导致：

- #215 难以获得稳定的 industry-side 模板入口。
- #148 无法得到可复用的行业包接入样例。
- #216 可能被迫反向定义本应由插件资产决定的模板来源。
- Plugin Detail / Plugins Index 中关于 Industry `SourceBinding` 的展示语义缺少稳定真源。

本 change 只解决行业包插件资产如何声明 `source_bindings`、模板文件该放在哪里、样例最少长什么样；不实现任何 runtime、持久化或业务逻辑。

## 改动

- 定义行业包 `plugin.yaml` 中 `source_bindings` 条目的最小可读字段与禁止写入内容。
- 定义行业包内 `templates/source_bindings/` 目录作为 `config_template` 的默认落点，并明确命名与相对路径约束。
- 定义行业包 README / usage note 对 `source_bindings` 模板的最小说明义务。
- 定义一个最小官方样例行业包骨架，覆盖 `required` source、`optional` source 与默认 override 模板。
- 明确行业包模板层与 #215 的模板契约、#216 的持久化模型、#148 的 source 插件边界之间的职责分离。

## 能力

### 新增能力

- `industry-source-bindings-manifest-template-v1`：定义行业包 `source_bindings` 的 manifest/template 目录约定、样例边界和非目标。

## 非目标

- 不定义 `SourceBinding Template` 与 `Effective Config` 的完整字段契约；这些由 #215 收口。
- 不定义 `SourceBinding` / `SchedulerRun` ORM、repository、service 或 migration；这些由 #216 收口。
- 不实现 RSS、Readability、Jina 或其他 source 插件代码；这些由 #148 或后续插件 issue 收口。
- 不实现 API、Web、Registry、Scheduler、Worker、Event Bus 或 RawEvent 入库逻辑。
- 不提交行业业务规则、私有关键词或真实 secret。

## 影响

- `openspec/changes/industry-source-bindings-manifest-template-v1/**`：作为 #225 的唯一 OpenSpec 真源。
- `plugins/industries/**`：后续实现行业包时应复用本 change 的目录与样例约定。
- `docs/design/07-industry-package-design.md`、`docs/design/06-source-plugin-design.md`：作为本 change 的架构依据，不在本 PR 中修改。
- #148、#215、#216：作为边界协同 issue，本 change 不替代它们各自的契约与实现范围。
