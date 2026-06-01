## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含 `industry-source-bindings-manifest-template-v1` 的 proposal、design、tasks、spec 和必要元数据。
- [x] 1.2 在 PR 说明中明确：本 PR 只定义行业包 `source_bindings` 的 manifest/template 目录与样例约定，不实现插件代码、runtime、持久化或调度逻辑。
- [ ] 1.3 等维护者在 OpenSpec-only PR #229 下明确评论“没问题”或批准后，再进入任何行业包样例或实现代码 PR。
  - 当前状态：截至 2026-06-01，PR #229 仍未获得维护者明确评论“没问题”或批准；当前实现 PR #234 必须标记为 `blocked-on-#229` / `do-not-merge-until-approved`，不能把该 gate 视为已完成。
## 2. Manifest 与模板目录约定

- [x] 2.1 固定行业包 `plugin.yaml` 中 `source_bindings` 条目的最小字段：`source_plugin_id`、`required`、`config_template`。
  - Inputs: #225、`docs/design/07-industry-package-design.md`、`docs/design/06-source-plugin-design.md`
  - Outputs: 可审查的 manifest 字段边界与禁止写入项
  - Write scope: `specs/industry-source-bindings-manifest-template-v1/spec.md`
- [x] 2.2 固定 `templates/source_bindings/` 为 `config_template` 的默认目录，并定义 `<source-name>.<purpose>.yaml` 命名方式。
  - Inputs: #225、`docs/prd/pages/10-plugins-index.md`、`docs/prd/pages/11-plugin-detail.md`
  - Outputs: 稳定的模板路径与命名约定
  - Write scope: `design.md`、`specs/industry-source-bindings-manifest-template-v1/spec.md`
- [x] 2.3 固定 `config_template` 使用插件根目录内相对路径，不允许越过插件目录边界。
  - Inputs: plugin manifest-first 方向、core/plugin gate
  - Outputs: 路径安全与可移植性边界
  - Write scope: `design.md`、`specs/industry-source-bindings-manifest-template-v1/spec.md`

## 3. 样例与 usage note 约定

- [x] 3.1 定义最小样例行业包骨架，至少覆盖一个 `required` source 和一个 `optional` source。
  - Inputs: #148、#225、`docs/design/07-industry-package-design.md`
  - Outputs: 可复用的目录样例和语义说明
  - Write scope: `design.md`、`specs/industry-source-bindings-manifest-template-v1/spec.md`
- [x] 3.2 固定 README / usage note 需要解释模板用途、required/optional 语义、不要写什么，以及与 #215 / #216 的职责边界。
  - Inputs: 工程质量 gate、core/plugin gate、#215、#216
  - Outputs: 最小说明义务，避免约束只藏在文件命名里
  - Write scope: `design.md`、`specs/industry-source-bindings-manifest-template-v1/spec.md`

## 4. 边界对齐

- [x] 4.1 明确本 change 不定义 effective config 合成、secret 解引用、运行态状态字段或持久化模型。
  - Inputs: #215、#216
  - Outputs: 与 contract / persistence issue 不重叠的职责边界
  - Write scope: `proposal.md`、`design.md`、`specs/industry-source-bindings-manifest-template-v1/spec.md`
- [x] 4.2 明确样例只表达 industry-side 声明，不反向定义 RSS 或 reader source 插件实现细节。
  - Inputs: #148、source plugin design
  - Outputs: 与 source plugin issue 的清晰接口边界
  - Write scope: `proposal.md`、`design.md`

## 5. 验证

- [x] 5.1 运行 `openspec validate industry-source-bindings-manifest-template-v1 --type change --strict --json`。
- [x] 5.2 人工检查 PR diff 仅包含本 change 目录，不混入实现代码、依赖升级、格式化噪音或其他未跟踪 change。
