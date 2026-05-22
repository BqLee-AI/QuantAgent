## 1. OpenSpec 评审

- [x] 1.1 提交 OpenSpec-only PR，只包含本 change 的 proposal、design、specs、tasks 和必要元数据。
- [x] 1.2 在 PR 说明中写清楚：本 PR 只定义插件 Registry V1 方案，不实现代码、不加载插件、不接交易执行。
- [x] 1.3 等维护者在 OpenSpec PR 下明确评论“没问题”或批准后，再开实现 PR。

## 2. Core Registry 模型

- [x] 2.1 在 `packages/core/src/quantagent/core/registry/` 定义 `PluginManifest`、`PluginType`、`PluginStatus`、`PluginRecord` 和结构化 `PluginError`。
- [x] 2.2 校验 `plugin.yaml` 必填字段：`id`、`name`、`type`、`version`、`entrypoint`、`capabilities`、`config_schema`。
- [x] 2.3 将输入类型 `executor` 兼容映射为 canonical `trade_executor`，但不实现真实执行能力。
- [x] 2.4 校验 `config_schema` 指向插件目录内存在的 JSON Schema 文件。

## 3. Registry 扫描器

- [x] 3.1 扫描 `plugins/` 与 `runtime/plugins/`，并在 runtime 目录不存在时清晰降级为空。
- [x] 3.2 为每个 `plugin.yaml` 生成 `PluginRecord`，包含来源、路径、manifest 摘要、状态和 `last_error`。
- [x] 3.3 单个插件 YAML 解析失败、缺字段、未知类型或 schema 缺失时，只标记该插件非法，不中断整体扫描。
- [x] 3.4 检测重复插件 ID，同 ID 多版本 V1 先标记冲突，不做依赖或版本求解。
- [x] 3.5 扫描过程不得 import 或执行 manifest 中的 `entrypoint`。

## 4. API 管理面

- [ ] 4.1 新增 `GET /api/v1/plugins`，返回统一 envelope 的插件列表。
- [ ] 4.2 新增 `GET /api/v1/plugins/{plugin_id}`，返回插件详情或统一 404 envelope。
- [ ] 4.3 新增 `GET /api/v1/plugins/{plugin_id}/config-schema`，返回配置 JSON Schema 或清晰错误。
- [ ] 4.4 新增 `POST /api/v1/plugins/actions/rescan`，触发重新扫描并返回扫描摘要。
- [ ] 4.5 API route 只调用 core Registry，不直接解析 YAML、不 import 插件代码、不返回 ORM model。

## 5. 验证

- [x] 5.1 测试合法 placeholder plugin 可被扫描并返回。
- [x] 5.2 测试 `runtime/plugins` 不存在时扫描仍成功。
- [x] 5.3 测试缺少 `plugin.yaml` 的目录被忽略。
- [x] 5.4 测试 manifest 缺必填字段、未知插件类型、config schema 缺失均返回 `invalid + last_error`。
- [x] 5.5 测试重复插件 ID 被检测并标记冲突。
- [ ] 5.6 测试 API 列表、详情、schema 查询、rescan 返回统一 envelope。
- [x] 5.7 运行与变更范围匹配的 Python 测试，并运行 `openspec validate plugin-registry-v1 --type change --strict --json`。

## 6. 后续插件 demo 边界

- [ ] 6.1 V1.1 单独设计最小官方 demo 插件，用于说明插件作者如何组织 `plugin.yaml`、`config.schema.json` 和最小 entrypoint。
- [ ] 6.2 demo 插件优先采用 `source` 类型，只做只读或 mock 输出，不接真实外部副作用。
- [ ] 6.3 demo 插件必须通过 Registry 扫描进入系统，不允许核心代码硬编码 class、import 列表或 if/else。
- [ ] 6.4 demo 插件后续可作为 RuntimeContext、生命周期、ToolRegistry 或 RawEvent 链路的验收样例，但这些能力不混入 V1 Registry 实现。
