# AGENTS.md

## 定位

- `packages/contracts` 是跨语言契约的预留 package。
- 该目录面向 OpenAPI、JSON Schema、Zod schema 和生成后的类型产物。
- 当前目录尚未落地实现，只保留 package 边界。

## 行为约束

- 不在没有 issue 或 OpenSpec 支撑的情况下提前生成大量契约文件。
- 契约变更会影响前后端和插件，应保持 PR 范围清晰并补充验证说明。
- 生成产物必须可由仓库命令重建；不能手写修改生成后的类型来绕过源 schema。
- 契约命名应表达业务含义，不暴露数据库内部表结构或实现细节。
- Python 和 TypeScript 不直接共享业务代码，只共享 OpenAPI、JSON Schema、Zod schema 和生成类型。
- REST client 从 OpenAPI 生成，稳定领域对象从 JSON Schema 生成 TypeScript 类型和 Zod schema。
- API DTO、Event DTO、Plugin DTO 和 ORM model 必须分层，不能用数据库模型替代跨语言契约。
- 新增或破坏契约时，PR 必须关联 issue/OpenSpec/design 真源，并说明前后端验证证据。
