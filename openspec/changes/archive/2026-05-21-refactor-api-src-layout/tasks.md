## Status

- 当前状态：实现已完成，等待 implementation PR 收口。
- OpenSpec-only PR #108 已获得继续实现所需确认。
- 当前实现已完成目录迁移、文档同步和验证，剩余收口项是 implementation PR 说明与 review。

## Graph Overview

关键路径是 `B0 -> V0 -> R0 -> R1 -> B1 -> V1 -> B2 -> P1/P2/P3 -> M1 -> M2 -> D1/D2 -> V2 -> V3 -> R2`。

- `B0-V0-R0-R1`：完成 OpenSpec-only 校验和审核门槛，阻止未经审核的目录重构。
- `B1-V1-B2`：准备 implementation 分支，建立迁移前测试基线，并产出旧 import 兼容清单。
- `P1/P2/P3`：HTTP、Auth、API v1 route 三个迁移切片可在 `B2` 后并行，但每个切片必须遵守 disjoint write boundary。
- `M1`：统一合并 re-export、内部 import、route registration 和 OpenAPI 行为检查。
- `M2-D1/D2`：确认 API 外部行为未变后，同步 README/AGENTS。
- `V2-V3-R2`：最终验证、路径一致性检查和 PR 收口。

## Blocking Serial Path

- [x] B0. 确认 issue #105、`apps/api/README.md`、`apps/api/AGENTS.md`、`docs/design/01-tech-stack-and-project-structure.md` 和 `docs/design/08-api-and-websocket-design.md` 是本 change 的输入真源。
- [x] V0. 运行 `openspec validate refactor-api-src-layout --type change --strict --json`，确认 proposal、design、spec 和 tasks 通过 strict 校验。
- [x] R0. 创建 OpenSpec-only PR，范围只包含 `openspec/changes/refactor-api-src-layout/**`。
- [x] R1. 等待维护者在 OpenSpec-only PR 下明确评论“没问题”或批准，再进入代码实现。
- [x] B1. 创建或确认 implementation 分支基于已审核的 OpenSpec change 和最新目标主线；在 R1 完成前不得开始源码迁移。
- [x] B2. 用 `rg "quantagent\\.api\\.(auth|middleware|responses|errors|exceptions|routers\\.register)" apps/api/src apps/api/README.md apps/api/AGENTS.md` 确认旧 import 和文档引用面，并产出最小兼容 re-export 清单。

## Parallel Work After B2

- [x] P1. HTTP 传输层迁移。
  - 输入：B2 兼容清单、`design.md` Decision 1、`spec.md` 的 HTTP 边界 requirement。
  - 输出：响应信封、API 层错误类型、异常处理注册和 Request ID middleware 落入明确 HTTP 边界。
  - 写入边界：`apps/api/src/quantagent/api/http/**` 或同等 HTTP 边界目录，相关 import 和测试 import。
  - 依赖：B2。
  - 并行条件：不修改 Auth 行为和 API v1 registration 语义。
  - 节点验证：错误响应仍使用 `code/data/msg/error` envelope，响应 header 与错误体中的 `request_id` 保持一致。

- [x] P2. API 私有 Auth 模块拆分。
  - 输入：B2 兼容清单、`design.md` Decision 2、`api-cookie-session-auth` stable spec。
  - 输出：actor/capability、session/cookie、CSRF/dependency 和 audit context 拆入 `auth/` 边界；`refresh_session` 等活动续期逻辑归入 session/cookie 边界。
  - 写入边界：`apps/api/src/quantagent/api/auth/**` 或同等 auth package，旧 `auth.py` 的最小 re-export，`routers/auth.py` 中 auth import，相关测试 import。
  - 依赖：B2。
  - 并行条件：不修改 route path、OpenAPI tags、public/protected registration 真源。
  - 节点验证：login/logout/me、development auth bypass、production secure cookie 校验、session 签名、`/me` session refresh、capability guard 和 CSRF guard 行为不变。

- [x] P3. API v1 route registration 边界迁移。
  - 输入：B2 兼容清单、`design.md` Decision 3、`spec.md` 的 route registration requirement。
  - 输出：标准 API v1 route、debug route 和 registration helper 收敛到显式 `routers/v1/` 边界。
  - 写入边界：`apps/api/src/quantagent/api/routers/v1/**` 或同等 v1 route 边界，registration tests。
  - 依赖：B2。
  - 并行条件：不修改 HTTP envelope 实现和 Auth session/cookie 内部实现。
  - 节点验证：`STANDARD_API_V1_ROUTER_REGISTRATIONS` 和 public/protected 分类仍是 API v1 route 注册真源；production 环境仍不注册 debug route，非 production debug route 仍不加入 public allowlist。

## Merge / Integration Nodes

- [x] M1. 合并 P1/P2/P3 后统一收敛内部 import 和兼容入口。
  - 输入：P1、P2、P3 输出。
  - 输出：内部引用统一使用新路径；旧入口已从 `apps/api` 代码内移除，不再保留兼容 re-export。
  - 写入边界：`apps/api/src/quantagent/api/**`、`apps/api/src/tests/**`。
  - 依赖：P1、P2、P3。
  - 验证：运行 `rg "quantagent\\.api\\.(auth|middleware|responses|errors|exceptions|routers\\.register)" apps/api/src apps/api/README.md apps/api/AGENTS.md`，确认无旧入口残留命中。

- [x] M2. 人工确认 API 外部行为未变。
  - 输入：M1 后代码。
  - 输出：现有 API 路径、状态码、response_model、tags、envelope、public allowlist、protected-by-default、CSRF、`/me` session refresh、production secure cookie 和 debug production gating 未回归。
  - 写入边界：无，发现回归时回到对应 P/M 节点修复。
  - 依赖：M1。
  - 验证：对照 `spec.md` 的全部 scenario 和 `src/tests/test_app.py` 中相关断言。

## Documentation Nodes

- [x] D1. 更新 `apps/api/README.md`。
  - 输入：M1 后实际代码结构。
  - 输出：目录说明、新增 route 流程、auth/http/router 边界和最小验证命令与实际代码一致。
  - 写入边界：`apps/api/README.md`。
  - 依赖：M1。
  - 验证：README 不再引导新增代码使用旧路径，且仍说明 public/protected allowlist、Cookie Session、CSRF 和 debug production gating。

- [x] D2. 更新 `apps/api/AGENTS.md`。
  - 输入：M1 后实际代码结构。
  - 输出：关键目录索引和本地规则与实际代码一致，明确不新增空的 `services/repositories/domain/models/usecases` 等目录。
  - 写入边界：`apps/api/AGENTS.md`。
  - 依赖：M1。
  - 验证：AGENTS 与 README 不冲突，且继续收紧 `apps/api` 只承载 HTTP/API 传输层的边界。

## Review Checkpoints

- [x] R0. OpenSpec-only PR 创建后接受维护者 review。
- [x] R1. 维护者明确评论“没问题”或批准前，不进入 implementation PR。
- [x] R2. implementation PR 说明必须链接 issue #105 和 `refactor-api-src-layout` change，说明依据、改动摘要、验证结果、最小兼容入口和未验证风险。
- [x] R3. 如果实现发现 change 边界需要调整，先补 OpenSpec artifacts 并重新完成 R0/R1，不在 implementation PR 中夹带未审核的大幅 spec 修改。

## Validation Nodes

- [x] V0. OpenSpec 校验：`openspec validate refactor-api-src-layout --type change --strict --json`。
- [x] V1. 实现分支基线验证：`cd apps/api && uv run python -m unittest discover -s src/tests`，在迁移前执行。
- [x] V2. 迁移后 API 验证：`cd apps/api && uv run python -m unittest discover -s src/tests`。
- [x] V3. 文档路径一致性检查：`rg "routers/register|routers/v1|http/|auth/" apps/api/README.md apps/api/AGENTS.md apps/api/src apps/api/src/tests`，确认文档与代码只指向新路径。
- [x] V4. OpenSpec 收口校验：如 implementation 期间修改本 change artifacts，再运行 `openspec validate refactor-api-src-layout --type change --strict --json`。

## Multi-Agent Plan

维护者允许并行实现时，可以在 B2 后拆成 3 个不重叠切片：

- Worker A：P1 HTTP 传输层迁移，写入 HTTP 边界和相关 re-export。
- Worker B：P2 Auth 模块拆分，写入 auth 边界和 auth tests。
- Worker C：P3 API v1 route 边界迁移，写入 routers/v1 和 registration tests。

合并责任必须集中在 M1。并行 worker 不得同时编辑 README/AGENTS，不得修改彼此模块内部实现；D1/D2 必须等 M1 后由单一 owner 完成。若实现者只有一个人，按 P1 -> P2 -> P3 -> M1 串行执行即可，避免跨文件冲突。
