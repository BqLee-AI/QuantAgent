# Plugin Schema 设计

## 设计依据

本文档根据 `docs/design/03-plugin-system-and-registry.md` 和
`docs/design/04-database-and-persistence-design.md` 收敛 Plugin 相关数据库 schema。

插件持久化采用“文件作为插件包来源，数据库作为运行时状态真源”的模型：

- 文件系统保存插件包静态内容，例如 `plugin.yaml`、`config.schema.json`、`src/` 和 `README.md`。
- 数据库保存系统实际安装了什么插件、当前启用哪个版本、配置是什么、依赖状态是什么、当前运行状态是什么。
- Registry 对外提供插件状态时，以数据库记录为准，不以实时扫描文件目录作为运行时真源。

初版插件 schema 包含四张表：

```text
plugin_records
plugin_versions
plugin_configs
plugin_dependency_records
```

本文档不设计 ToolRegistry、Skill Registry、SourceBinding、插件市场、签名校验或完整
`audit_logs` 表；这些能力后续单独设计。

## 表关系

```text
plugin_records 1 ── 0..n plugin_versions
plugin_records 1 ── 0..n plugin_configs
plugin_versions 1 ── 0..n plugin_dependency_records
```

- `plugin_records` 是同一插件 ID 的主记录。
- `plugin_versions` 保存该插件的每个版本快照。
- `plugin_configs` 保存配置快照，配置必须绑定具体插件版本。
- `plugin_dependency_records` 保存某个插件版本声明的依赖和 Registry 解析结果。

## 枚举与状态

### `plugin_type`

| 值 | 说明 |
| --- | --- |
| `source` | 数据源插件，负责采集、接收和标准化原始信息 |
| `industry` | 行业包插件，负责事件行业分析、工具、Skill 和市场映射 |
| `strategy` | 策略插件，负责把分析结果映射为策略建议 |
| `notification` | 通知插件，负责 UI 或外部通知 |
| `executor` | 执行器插件，初版只允许 disabled、虚盘或 mock 路径；虚盘对应协议值 `dry_run` |

### `plugin_source`

| 值 | 说明 |
| --- | --- |
| `official` | 仓库 `plugins/` 下随代码分发的官方插件 |
| `runtime` | `runtime/plugins/` 下运行时安装的插件 |
| `git` | 从 Git URL 导入的插件 |
| `zip` | 从本地 zip 导入的插件 |
| `private_dir` | 从私有目录导入的插件 |
| `local` | 本地实验插件 |

### `plugin_status`

| 值 | 说明 |
| --- | --- |
| `discovered` | Registry 已发现插件文件，但尚未完成校验 |
| `validated` | manifest 和 config schema 已校验通过 |
| `installed` | 插件已注册到数据库，但未完成配置或加载 |
| `configured` | 插件已有 active 配置 |
| `loaded` | 插件实例已创建但未开始运行 |
| `started` | 插件已启动 |
| `stopped` | 插件已停止但未禁用 |
| `reloaded` | 插件最近完成 reload |
| `disabled` | 插件被禁用 |
| `uninstalled` | 插件已软卸载，历史记录保留 |
| `failed` | 插件运行或生命周期操作失败 |
| `installed_but_blocked` | 插件已安装，但依赖、配置或安全策略阻塞启用 |

### `executor_runtime_mode`

| 值 | 说明 |
| --- | --- |
| `disabled` | 执行器不可执行任何动作 |
| `dry_run` | 执行器只允许虚盘，不操作实盘 |
| `mock` | 执行器只允许 mock 执行 |

初版不支持实盘交易执行模式。真实执行需要后续单独设计权限、风险、审批和审计闭环。

## `plugin_records`

### 用途

`plugin_records` 是 Registry 的插件主索引，用于回答：

- 系统当前知道哪些插件。
- 插件当前状态是什么。
- 当前 active 版本是哪一个。
- 最近一次阻塞或错误原因是什么。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 数据库内部主键，不等同于 manifest `id` |
| `plugin_id` | `text` | not null, unique | manifest 中声明的全局插件 ID，例如 `quantagent.official.source.rss` |
| `type` | `text` | not null | 插件类型，按 `plugin_type` 值约束，用于区分 source、industry、strategy、notification、executor |
| `name` | `text` | not null | 当前展示名，来自 active version 的 manifest |
| `source` | `text` | not null | 插件来源，按 `plugin_source` 值约束，用于区分官方插件、runtime 插件、Git、zip 或私有目录导入 |
| `status` | `text` | not null | 插件当前运行时状态，按 `plugin_status` 值约束，不代表某个版本的校验状态 |
| `active_version_id` | `uuid` | nullable | 当前 active 版本 ID；插件未安装、未校验或卸载后可以为空 |
| `installed_version` | `text` | nullable | 当前 active 版本号的冗余字段，便于列表查询和 UI 展示 |
| `install_path` | `text` | nullable | 当前 active 插件根目录路径 |
| `executor_mode` | `text` | nullable | 仅 executor 插件使用，按 `executor_runtime_mode` 值约束；初版默认 `disabled`，非 executor 插件应为空 |
| `enabled_at` | `timestamptz` | nullable | 最近一次启用成功的时间 |
| `disabled_at` | `timestamptz` | nullable | 最近一次停用或禁用成功的时间 |
| `uninstalled_at` | `timestamptz` | nullable | 插件软卸载时间；软卸载不删除历史记录 |
| `blocked_reason_code` | `text` | nullable | 插件被阻塞的结构化原因码，例如 `missing_dependency`、`invalid_config` |
| `blocked_reason_message` | `text` | nullable | 插件被阻塞的脱敏原因摘要，供 UI 和排查使用 |
| `last_error_code` | `text` | nullable | 最近一次运行或生命周期失败的结构化错误码 |
| `last_error_message` | `text` | nullable | 最近一次错误的脱敏摘要，不保存 secret 或敏感参数 |
| `last_error_at` | `timestamptz` | nullable | 最近一次错误发生时间 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、私有策略或敏感工具参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 主记录创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 主记录最近更新时间 |

### 约束与索引

- `unique(plugin_id)`，同一个插件 ID 只有一条主记录。
- `index(type, status)`，支持按插件类型和状态筛选。
- `index(status, updated_at desc)`，支持插件工作台按状态排序。
- `index(active_version_id)`，支持从 active version 回查主记录。
- `active_version_id` 逻辑引用 `plugin_versions.id`。由于 `plugin_records.active_version_id` 与 `plugin_versions.plugin_record_id` 会形成循环外键，初版建议不建数据库外键，由 Registry/service 事务保证引用有效；如果后续需要 DB 约束，应使用 nullable 后置更新和 deferrable FK。
- 同一插件 ID 同一时间只能有一个 active version，由 `active_version_id` 和 Registry 事务保证。

### 写入规则

- Registry 扫描文件目录后，必须写入或更新数据库记录，再对外暴露运行时状态。
- `status` 表示插件当前运行时状态；某个版本校验失败时，不应直接覆盖可用旧版本的状态。
- 卸载采用 soft delete：设置 `status = uninstalled` 和 `uninstalled_at`，不得级联删除版本、配置、依赖或历史业务记录。

## `plugin_versions`

### 用途

`plugin_versions` 保存同一插件 ID 的各版本快照，用于支持升级、降级、reload、历史回查和文件变更检测。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 插件版本记录 ID |
| `plugin_record_id` | `uuid` | not null, foreign key | 所属插件主记录 ID |
| `plugin_id` | `text` | not null | manifest 中的插件 ID，冗余保存便于查询和排查 |
| `version` | `text` | not null | manifest 中声明的版本号；语义版本比较由 Registry/service 层处理 |
| `entrypoint` | `text` | not null | manifest 中声明的入口，例如 `rss_plugin:plugin` |
| `manifest_path` | `text` | not null | `plugin.yaml` 文件路径 |
| `install_path` | `text` | not null | 插件版本所在根目录 |
| `package_source` | `text` | nullable | 插件包来源，例如 Git URL、本地 zip 路径或私有目录 |
| `package_checksum` | `text` | nullable | 插件包或目录快照校验摘要，用于重复安装和篡改排查 |
| `manifest` | `jsonb` | not null | 校验后的 manifest 完整快照 |
| `manifest_hash` | `text` | not null | manifest 稳定 hash，用于判断 manifest 是否变化 |
| `config_schema` | `jsonb` | nullable | 校验后的配置 schema 快照；无配置插件可以为空 |
| `config_schema_hash` | `text` | nullable | config schema 稳定 hash，用于判断配置 schema 是否变化 |
| `capabilities` | `jsonb` | not null, default `[]` | manifest 中声明的 capabilities 数组快照 |
| `permissions` | `jsonb` | not null, default `[]` | manifest 中声明的 permissions 数组快照 |
| `dependencies` | `jsonb` | not null, default `{}` | manifest 中 dependencies 的原始快照 |
| `validation_status` | `text` | not null | 版本校验状态，建议值为 `pending`、`valid`、`invalid` |
| `validation_errors` | `jsonb` | not null, default `[]` | manifest 或 config schema 校验错误列表 |
| `installed_at` | `timestamptz` | not null, default `now()` | 该版本注册入库时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 该版本记录最近更新时间 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、私有策略或敏感工具参数 |

### 约束与索引

- `unique(plugin_record_id, version)`，同一插件主记录下同一版本只能注册一次。
- `index(plugin_id, version)`，支持按 manifest ID 和版本查询。
- `index(validation_status)`，支持筛选校验失败或待校验版本。
- `index(manifest_hash)`，支持判断 manifest 是否重复。
- `index(config_schema_hash)`，支持判断配置 schema 是否变化。
- `plugin_record_id` 外键引用 `plugin_records.id`，建议 `on delete restrict`。

### 写入规则

- 每次安装、升级或降级都应保存当时的 manifest 和 config schema 快照。
- `manifest_hash` 和 `config_schema_hash` 应基于稳定序列化内容计算。
- 新版本 `invalid` 不应破坏旧版本继续运行；Registry 应保留旧 active version，除非维护者明确切换。
- 插件版本号以 `text` 保存，避免数据库层过早绑定某一种版本比较规则。

## `plugin_configs`

### 用途

`plugin_configs` 保存插件运行时配置快照，用于 schema-driven form、配置校验、reload 判断、配置回滚和审计串联。

配置必须绑定具体 `plugin_version_id`，因为不同插件版本的 config schema 可能不同。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 配置快照 ID |
| `plugin_record_id` | `uuid` | not null, foreign key | 所属插件主记录 ID |
| `plugin_version_id` | `uuid` | not null, foreign key | 配置适用的插件版本 ID |
| `version` | `integer` | not null | 配置快照版本号，在同一插件主记录内递增 |
| `status` | `text` | not null | 配置状态，建议值为 `draft`、`active`、`superseded`、`invalid`、`archived` |
| `config` | `jsonb` | not null, default `{}` | 运行时配置；敏感项只保存 `secret://...` 引用或加密值引用 |
| `sensitive_fields` | `jsonb` | not null, default `[]` | 敏感字段路径数组，可由 config schema 推导或在校验后固化 |
| `schema_hash` | `text` | not null | 创建该配置时使用的 config schema hash |
| `requires_reload` | `boolean` | not null, default `false` | 配置变更是否要求插件 reload |
| `validation_status` | `text` | not null | 配置校验状态，建议值为 `pending`、`valid`、`invalid` |
| `validation_errors` | `jsonb` | not null, default `[]` | 配置校验错误列表 |
| `validated_at` | `timestamptz` | nullable | 最近一次校验完成时间 |
| `activated_at` | `timestamptz` | nullable | 该配置成为 active 配置的时间 |
| `created_by_type` | `text` | nullable | 创建配置的 actor 类型，例如 `user`、`system`、`plugin` |
| `created_by` | `text` | nullable | 创建配置的 actor ID、模块名或插件 ID |
| `request_id` | `text` | nullable | 创建或更新配置的请求 ID，用于串联 API 请求和审计 |
| `archived_at` | `timestamptz` | nullable | 配置被归档或软删除的时间；为空表示未归档 |
| `archived_by_type` | `text` | nullable | 执行归档的 actor 类型，例如 `user`、`system` |
| `archived_by` | `text` | nullable | 执行归档的 actor ID 或系统模块名 |
| `archived_reason` | `text` | nullable | 配置归档原因摘要，必须脱敏 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、私有策略或敏感工具参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 配置快照创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 配置快照最近更新时间 |

### 约束与索引

- `unique(plugin_record_id, version)`，同一插件下配置版本号不能重复。
- 部分唯一索引：同一 `plugin_record_id` 同一时间只能有一个 `status = active`。
- `index(plugin_record_id, status)`，支持读取插件当前 active 配置或历史配置。
- `index(plugin_version_id)`，支持按插件版本查找配置。
- `index(schema_hash)`，支持发现配置是否基于旧 schema。
- `index(request_id)`，支持按请求追踪配置变更。
- `index(archived_at)`，支持管理台筛选已归档配置。
- `plugin_record_id` 外键引用 `plugin_records.id`，建议 `on delete restrict`。
- `plugin_version_id` 外键引用 `plugin_versions.id`，建议 `on delete restrict`。
- `plugin_configs.plugin_record_id` 必须与关联 `plugin_versions.plugin_record_id` 一致；落地时可通过复合外键约束或 service 层写入校验保证。

### 写入规则

- 数据库不长期保存 `masked_config`，避免 masked view 与真实配置漂移。
- 写入或更新配置状态时，必须校验 `plugin_record_id` 与 `plugin_version_id` 的归属一致性。
- API 返回配置时，应根据 `config_schema` 和 `sensitive_fields` 动态生成 masked view。
- 配置中的敏感项默认保存 secret reference，例如 `secret://x_api/main`。
- 确实必须入库的敏感值需要先加密，并且 API、日志和测试断言不得输出原文。
- 插件升级后，如果 `config_schema_hash` 变化，应创建新的配置快照或标记旧配置需要迁移，不直接复用旧 active 配置。
- 配置删除采用归档语义：设置 `status = archived` 和 `archived_at` 等字段，不物理删除历史配置快照。
- 配置更新必须写统一审计日志；本表只保存配置快照，不替代 `audit_logs`。

## `plugin_dependency_records`

### 用途

`plugin_dependency_records` 保存某个插件版本声明的依赖、Registry 解析结果和自动安装状态，用于依赖检查、阻塞原因展示、自动安装审计和故障排查。

### 字段

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | `uuid` | primary key | 依赖记录 ID |
| `plugin_record_id` | `uuid` | not null, foreign key | 声明该依赖的插件主记录 ID |
| `plugin_version_id` | `uuid` | not null, foreign key | 声明该依赖的插件版本 ID |
| `dependency_type` | `text` | not null | 依赖类型，建议值为 `plugin`、`python`、`system` |
| `dependency_name` | `text` | not null | 依赖名称；插件依赖为插件 ID，Python 依赖为包名，system 依赖为能力名 |
| `version_constraint` | `text` | nullable | 版本约束，例如 `>=0.1.0`；无版本要求时为空 |
| `required` | `boolean` | not null, default `true` | 是否必需；可选依赖缺失时不应阻塞插件主流程 |
| `declared_dependency` | `jsonb` | not null, default `{}` | manifest 中该依赖声明的原始 JSON 快照 |
| `status` | `text` | not null | 依赖状态，建议值为 `pending`、`satisfied`、`missing`、`installing`、`installed`、`blocked`、`failed` |
| `resolved_plugin_record_id` | `uuid` | nullable, foreign key | 插件依赖解析到的插件主记录 ID，仅 `dependency_type = plugin` 时使用 |
| `resolved_plugin_version_id` | `uuid` | nullable, foreign key | 插件依赖解析到的插件版本 ID，仅 `dependency_type = plugin` 时使用 |
| `resolved_version` | `text` | nullable | 已解析或已安装的版本号 |
| `install_attempted` | `boolean` | not null, default `false` | Registry 是否尝试过自动安装该依赖 |
| `install_source` | `text` | nullable | 自动安装使用的来源，例如 Git URL、插件源名称或本地路径 |
| `blocked_reason_code` | `text` | nullable | 依赖阻塞原因码，例如 `system_dependency_missing`、`version_conflict` |
| `blocked_reason_message` | `text` | nullable | 依赖阻塞原因的脱敏摘要 |
| `last_checked_at` | `timestamptz` | nullable | 最近一次依赖检查时间 |
| `last_error_code` | `text` | nullable | 最近一次依赖安装或解析失败的错误码 |
| `last_error_message` | `text` | nullable | 最近一次依赖错误的脱敏摘要 |
| `metadata` | `jsonb` | not null, default `{}` | 扩展信息，不能保存 secret、私有策略或敏感工具参数 |
| `created_at` | `timestamptz` | not null, default `now()` | 依赖记录创建时间 |
| `updated_at` | `timestamptz` | not null, default `now()` | 依赖记录最近更新时间 |

### 约束与索引

- `unique(plugin_version_id, dependency_type, dependency_name, version_constraint)`，避免同一版本重复记录同一依赖。
- `index(plugin_record_id, status)`，支持查看插件被哪些依赖阻塞。
- `index(plugin_version_id, status)`，支持查看某个版本的依赖解析状态。
- `index(dependency_type, dependency_name)`，支持查找依赖被哪些插件使用。
- `index(resolved_plugin_record_id)`，支持检查插件反向依赖。
- `plugin_record_id` 外键引用 `plugin_records.id`，建议 `on delete restrict`。
- `plugin_version_id` 外键引用 `plugin_versions.id`，建议 `on delete restrict`。
- `resolved_plugin_record_id` 外键引用 `plugin_records.id`，建议 `on delete restrict`。
- `resolved_plugin_version_id` 外键引用 `plugin_versions.id`，建议 `on delete restrict`。
- `plugin_dependency_records.plugin_record_id` 必须与关联 `plugin_versions.plugin_record_id` 一致；落地时可通过复合外键约束或 service 层写入校验保证。
- 当 `resolved_plugin_record_id` 和 `resolved_plugin_version_id` 同时非空时，`resolved_plugin_record_id` 必须与关联 `plugin_versions.plugin_record_id` 一致。

### 写入规则

- 依赖记录必须同时保留 manifest 原始声明和 Registry 解析结果。
- 写入依赖记录时，必须校验声明方和解析结果中的 `plugin_record_id` / `plugin_version_id` 归属一致性。
- `plugin` 依赖可尝试从已配置插件源自动安装。
- `python` 依赖只能通过受控安装流程安装到插件运行环境，不污染主 Python 环境。
- `system` 依赖初版只检查不自动安装。
- 自动安装、安装失败、阻塞和解除阻塞都必须写统一审计日志。

## 生命周期写入规则

### 安装

安装流程应在事务边界内写入或更新：

- `plugin_records` 主记录。
- `plugin_versions` 版本快照。
- `plugin_dependency_records` 依赖声明和初始解析状态。

如果 manifest 或 config schema 校验失败：

- 新版本 `plugin_versions.validation_status` 记为 `invalid`。
- `plugin_records.status` 可记为 `failed` 或 `installed_but_blocked`，但不应破坏旧 active version。

### 配置

配置更新应创建新的 `plugin_configs` 快照，不直接覆盖历史配置。

- 校验通过后可将新配置设为 `active`。
- 同一插件只能有一个 active config。
- 旧 active config 应标记为 `superseded`。
- 配置删除或清理只允许标记为 `archived`，不得物理删除历史配置快照。
- 配置变更后是否 reload 由 `requires_reload`、manifest 和 Registry 共同决定。

### 启用

启用插件前必须检查：

- `plugin_records.active_version_id` 存在。
- active version `validation_status = valid`。
- 存在 active config，或插件 schema 允许空配置。
- 必需依赖均为 `satisfied` 或等价可用状态。
- executor 插件的 `executor_mode` 不是空值，且初版只能是 `disabled`、`dry_run` 或 `mock`；其中 `dry_run` 表示虚盘，不操作实盘。

### 停用、reload、卸载

- 停用更新 `plugin_records.status`、`disabled_at` 和必要错误字段。
- reload 成功后可更新 `status = reloaded`，随后由 Registry 进入 `started` 或 `stopped`。
- 卸载只做 soft delete，不删除版本、配置、依赖、事件、分析结果、审批记录或审计记录。

## 验证建议

落地 ORM model 和 Alembic migration 时，至少验证：

- 空库 upgrade 后包含四张插件表、枚举、外键和关键索引。
- 同一 `plugin_id` 不能创建多条 `plugin_records`。
- 同一插件同一版本不能创建多条 `plugin_versions`。
- 同一插件同一时间只能有一个 active config。
- 新版本校验失败不会删除或覆盖旧 active version。
- `plugin_configs` 不返回 secret 原文，API 动态生成 masked view。
- 依赖记录能区分 manifest 原始声明和 Registry 解析结果。
- 卸载插件不会级联删除历史版本、配置、依赖和业务记录。

## 后续扩展

- SourceBinding 属于调度和行业包引用关系，后续单独设计。
- ToolRegistry 和 Skill Registry 属于运行时能力治理，后续单独设计。
- 统一 `audit_logs` 落地后，插件安装、升级、降级、启停、reload、配置变更、依赖自动安装和卸载都应写 audit。
- 插件签名、来源白名单、插件市场和复杂依赖冲突求解不进入初版 schema。
