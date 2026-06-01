## 1. OpenSpec Review Gate

- [x] 1.1 运行 `openspec validate source-binding-effective-config-contract-v1 --type change --strict --json`，并保持 PR 范围仅包含本 change 的 proposal、design、tasks、specs 和必要说明。
- [x] 1.2 提交 issue #215 的 OpenSpec-only PR，在 PR 说明中明确“只定义契约，不实现业务代码”。
- [x] 1.3 等待维护者明确评论“没问题”或批准后，再进入任何 `packages/core`、`packages/plugin-sdk`、`plugins/**`、`apps/scheduler` 或 `apps/api` 实现。

## 2. Core Contract Implementation

- [x] 2.1 在 `packages/core/src/quantagent/core/source_binding/` 落地 `SourceBindingTemplate` 平台模型、template loader 和 policy hint 校验对象。
- [x] 2.2 在 `packages/core/src/quantagent/core/source_binding/effective_config.py` 落地 source defaults、template ref 内容、inline override 与 policy 对象的合成器。
- [x] 2.3 为 `EffectiveSourceConfig` 增加 `config_fingerprint`、`template_refs`、`validated_at` 等可审计快照字段，并保持 JSON-safe。
- [x] 2.4 在 secret 注入边界附近补短中文注释，明确“为什么只持久化 secret ref、不持久化明文”。

## 3. Downstream Integration Gates

- [ ] 3.1 在 `#216` 中把 `EffectiveSourceConfig` 快照映射到 `SourceBinding` 持久化模型，但不把 runtime-resolved secret 写入 ORM。
- [ ] 3.2 在 `#217` 中让 scheduler 直接消费持久化快照与 policy 对象，不在调度循环里重算 merge。
- [ ] 3.3 在 `#225` 中把行业包 manifest/template 资产映射到 `config_template_ref`、`config_override` 和 policy hint，而不是重新定义字段。
- [ ] 3.4 在 `#226` 中仅暴露脱敏 summary、fingerprint 和允许的动作上下文，不公开 runtime-resolved config。

## 4. Verification

- [x] 4.1 为合并优先级编写最小测试：source defaults < template asset < inline override < platform metadata。
- [x] 4.2 为失败路径编写最小测试：未知字段、非法 `null` 覆盖、缺失 source schema、policy shape 不合法。
- [x] 4.3 为 secret 边界编写最小测试：持久化 / 审计层只看到 `secret_ref`，runtime 执行层才看到解引用结果。
- [x] 4.4 为插件边界编写最小测试或 review gate：source plugin 只能消费平台传入的 validated config，不自行 merge override 或读取 secret 真源。
