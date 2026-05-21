## Context

issue #106 建立在 issue #97 的前端 Cookie Session 登录接入之上。本 change 以 “#97 已合入或至少已被维护者接受为实现基线” 为前提；在该前提下，前端将具备以下基础：

- `GET /api/v1/me` 会返回 `actor_id`、`actor_type`、`capabilities` 和 `csrf_token`。
- `AuthProvider` 已维护统一登录态，并通过 shared API client 集中处理 401/403。
- workspace 路由已经能区分公共 `/login` 和受保护管理台。
- `MainLayout` 已展示 actor 和 development bypass 状态，但没有 capability-aware 的导航或页面入口语义。

与此同时，设计文档已经给出长期边界：前端应基于 capability 控制入口可见性，403 权限不足需要展示 `request_id`，但后端 capability guard 仍是真源。当前代码离这个目标只差一层统一 policy；如果各页面单独补，会形成 capability 字符串分叉、route guard 混乱和互相矛盾的 UX。

## Goals / Non-Goals

**Goals:**

- 定义 capability policy 的统一落点，供路由、导航和页面操作入口复用。
- 明确“未登录”和“已登录但 capability 不足”的差异化前端语义。
- 为 workspace 首批入口建立一致的可见性 / 禁用策略。
- 为页面级和操作级 403 建立统一 UX，并保留 request/trace 元数据入口。
- 保持后端 capability guard 为最终权限真源，前端只承担体验和预防误操作职责。

**Non-Goals:**

- 不实现多用户、角色层级、租户边界或完整 RBAC。
- 不建立新的后端 capability 枚举来源；仍消费 `/me` 返回的 capability snapshot。
- 不要求在本轮为所有未来业务 action 定义完备矩阵。
- 不把前端导航裁剪或按钮禁用当作真正的安全边界。
- 不在本轮引入 feature flag 系统、策略 DSL 或额外鉴权服务。

## Decisions

### 1. capability policy 放在 shared auth 边界，而不是页面各自维护

本 change 应在 `apps/web/src/shared/auth/` 下维护集中 capability policy：至少包括 capability 常量、route-to-capability 映射、high-risk action 分类和判断 helper。路由 guard、`MainLayout` 和后续页面只消费统一结果，不直接散落 capability 字符串。

替代方案是让每个页面在本地写 `capabilities.has("...")`。该方案短期快，但会让路由、导航和按钮判断各自漂移，因此不采用。

### 2. 首批 capability-to-route / action policy 先按现有 workspace 入口分层

首批 policy 只覆盖当前已有 capability 集和现有 workspace 入口，不为未来未落地资源提前扩展矩阵。当前建议基线如下：

| Policy target | Required capability | Missing capability behavior | Notes |
| --- | --- | --- | --- |
| `/events`, `/runtime`, `/skills`, `/tools`, `/industries` | `runtime.inspect` | route 进入受限页；对应导航项隐藏 | 这些入口当前更接近运行态/观测读取能力 |
| `/approvals` | `approval.approve` OR `approval.amend` | route 进入受限页；导航项隐藏 | 列表页允许按“任一审批能力可进入”处理 |
| `/plugins` | `plugin.configure` OR `plugin.install` | route 进入受限页；导航项隐藏 | route 层只决定是否可进入插件域 |
| `/settings` | `secret.manage` | route 进入受限页；导航项隐藏 | 当前最敏感后台入口 |
| Plugin install action | `plugin.install` | `disabled-with-reason` | 入口可保留，但不得自行触发请求 |
| Plugin configure / enable / disable action | `plugin.configure` | `disabled-with-reason` | 禁用态需要明确原因 |
| Approval approve / reject action | `approval.approve` | `disabled-with-reason` | capability 不足时不应先提交再等 403 |
| Approval amend action | `approval.amend` | `disabled-with-reason` | 与 approve 独立判断 |
| Executor dry-run action | `executor.dry_run` | `disabled-with-reason` | 高风险操作，优先保留显式禁用态 |
| Secret reveal / update action | `secret.manage` | `disabled-with-reason` | 不因 capability 不足泄露敏感值 |

替代方案是先不定义基线映射，等真实页面落地后再补。该方案会让每个页面都先各自发明 capability 字符串和 UX，因此不采用。

### 3. 路由层必须区分 unauthenticated 与 forbidden

未登录仍沿用 `/login` 跳转语义；已登录但 capability 不足的访问不应被当成未登录，也不应回跳 `/login`。对这类请求，路由层需要渲染统一受限态或进入统一 403 页面壳，向用户明确表达“已认证但无权限”。

替代方案是 capability 不足也重定向到 `/login`。该方案会把权限不足伪装成身份失效，破坏当前 auth 语义，因此不采用。

### 4. navigation hiding、action disabling、受限页和操作级 403 分别服务不同场景

四类表现应明确分层，而不是页面自行挑一种：

| UX outcome | Applies to | Why |
| --- | --- | --- |
| `redirect:/login` | 未登录访问受保护路由 | 这是身份问题，不是权限问题 |
| `forbidden-page` | 已登录但缺少 route 所需 capability，且用户通过直达 URL 或默认入口到达页面 | 需要保留“已认证但无权限”的明确语义 |
| `hidden` | 主导航或页面入口在当前 capability 下完全不可进入，且缺少该入口不会破坏主流程理解 | 避免无意义入口噪音 |
| `disabled-with-reason` | 用户应知晓但暂不可执行的高风险 action | 降低误操作，并清楚说明限制原因 |
| `operation-level-403` | policy 允许显示和尝试，但后端仍返回 403 | 兜底承接 policy 漏网或运行时状态差异 |

替代方案是所有缺权限入口都一律隐藏，或一律显示后点击报错。前者会降低可发现性，后者会把 403 变成常态交互，因此不采用。

### 5. 状态机必须清楚区分身份与权限

本 change 依赖的前端状态机如下：

| Auth state | Capability check | Route result | Action result |
| --- | --- | --- | --- |
| `unauthenticated` | not evaluated | redirect `/login` | not available |
| `authenticated + allowed` | pass | render target route | action enabled |
| `authenticated + forbidden` | fail | render forbidden page inside protected app semantics | action disabled or, if request still happens, operation-level 403 |

关键约束：

- route guard 只在 `unauthenticated` 时重定向 `/login`；
- capability 不足永远不是登录跳转问题；
- action policy 与 route policy 复用同一份 capability 映射，不允许页面自行推断。

替代方案是把 capability 判断揉进 auth 状态。该方案会让“未登录”和“已登录但无权限”难以区分，因此不采用。

### 6. 403 UX 分为页面级受限态和操作级提示两层

页面级访问受限时，优先展示稳定的页内受限态，包含权限不足说明、返回入口和排查信息；局部高风险操作失败时，优先复用现有错误治理能力，以非阻断提示呈现，并允许查看 `request_id` / `trace_id`。两类场景共享同一错误元数据来源，但不强迫用同一种容器。

替代方案是全部使用 toast 或全部使用 modal。单一容器无法同时处理页面级拦截和局部操作失败，因此不采用。

## Risks / Trade-offs

- [Risk] 当前许多 workspace 页面仍是占位态，过早固化 capability-to-route 映射可能与未来真实业务边界不完全一致。  
  -> Mitigation: review 时应能在 policy 表中清楚识别“route family mapping”与“action mapping”是两层；未落地页面不得引入新 capability 名称。

- [Risk] 隐藏与禁用混用可能让用户难以预期。  
  -> Mitigation: 验收时应能对照 policy 表核对每个入口属于 `hidden`、`disabled-with-reason` 还是 `forbidden-page`，同类入口不得混用。

- [Risk] 403 若没有统一 request/trace 展示方式，会回到“错误对象有字段但 UI 不可见”的状态。  
  -> Mitigation: 验收时必须覆盖页面级 forbidden 和操作级 403 两类场景，确认 `request_id` / `trace_id` 至少有一个可见入口。

- [Risk] 前端 policy 与后端 capability guard 可能暂时不完全同步。  
  -> Mitigation: 验收时必须保留“后端返回 403 时前端仍能正确展示”的场景，不能因为前端已有禁用态就跳过后端兜底。
