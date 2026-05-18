# AGENTS.md

## 定位

- 本文件是 QuantAgent 的 AI 开发行为规则与操作指引，不是项目计划、开发笔记或通用模板。
- 只记录已经适用于本仓库的长期规则，以及能减少重复错误的操作约束。
- 新规则必须来自项目实际边界、已经出现过的问题，或对项目有长期影响的协作约定。
- 不在这里写阶段性 TODO、临时想法、 speculative 设计，或尚未落地模块的复杂实现细节。

## 规则层级

- 用户在当前对话中的明确要求优先级最高。
- 越靠近被修改文件的 `AGENTS.md` 优先级越高。
- 下层 `AGENTS.md` 只补充或收紧上层规则，不能放宽根目录规则。
- 发现规则、设计文档与实际代码冲突时，先读取现有实现、issue 评论和 PR 讨论，再说明冲突，不要直接按想象改。

## 架构文档与真源

- `docs/design/` 是项目方向、模块边界和阶段性架构约定的主要参考，但不是一版钉死的实现命令。
- 实际开发中如果发现设计文档与实现成本、框架限制、业务边界或安全约束冲突，应在 PR 中说明取舍，并判断是否需要回写设计文档或 OpenSpec。
- 对项目有长期影响的规则，不能只留在对话里；应固化到合适的 `AGENTS.md`、`docs/design/` 或开 `openspec/`。
- 新 feature、破坏性变更、跨模块契约变更和风险边界变化必须关联真源：issue、OpenSpec change、设计文档段落或 PR 评论。
- PR 说明必须写清楚证据链：为什么这样改、依据来自哪里、验证了什么、还有哪些未验证风险。
- 设计文档只提供大方向时，以当前代码、用户最新确认和可运行验证结果作为落地依据。

## 控制面沉淀

- AI 发现重复提醒、长期边界、跨 issue 的共性错误或容易被模型误判的新技术栈规则时，应提醒用户是否沉淀到合适载体。
- 沉淀位置按性质选择：长期 AI 行为规则进最近层级的 `AGENTS.md`，架构边界进 `docs/design/`，产品验收和待确认业务问题进 `docs/prd/`，行为或契约变化进 `openspec/changes/`。
- 不把一次性调试结论、临时 workaround、未确认想法或当前分支的施工细节写进长期规则。
- 如果同一个判断已经在 issue、OpenSpec、design、tasks 或 PR 中出现，应优先链接和加固现有资产，不另造平行文档。
- 当用户提出新流程、模板或协作习惯时，AI 应先判断它是本次任务临时约束，还是值得沉淀的控制面资产，并明确提醒。

## 项目边界

- 本仓库是 monorepo：`apps/` 放运行入口，`packages/` 放共享能力，`plugins/` 放随代码分发的官方插件，`runtime/` 放本地运行数据。
- Python workspace 由根目录 `pyproject.toml` 管理，当前已纳入 `apps/api` 和 `packages/core`。
- Web workspace 由根目录 `package.json` 管理，当前前端应用在 `apps/web`。
- `apps/api` 是 FastAPI HTTP 边界，核心配置、数据库和可复用基础能力优先下沉到 `packages/core`。
- `packages/core` 是共享基础设施包，不能反向依赖 `apps/api`、`apps/web` 或具体插件实现。
- `docs/design/01-tech-stack-and-project-structure.md` 中的推荐结构是阶段方向；当前实现尚未落地的目录，只保持边界，不提前填满实现。
- `runtime/` 用于本地配置、日志、数据、私有插件和运行时缓存，不作为业务源码提交。

## Package 增长规则

- 新增 package、长期目录或共享抽象前，先判断现有 `apps/`、`packages/`、`plugins/`、`runtime/` 边界是否已经能承接。
- 只有存在明确复用方、稳定职责、依赖方向和真源依据时，才新增 package；不要为“以后可能会用”提前创建复杂抽象。
- `apps/` 可以依赖 `packages/`，`packages/core` 不能反向依赖 app、web 或具体插件实现。
- API 私有能力保留在 `apps/api`；被 worker、scheduler、插件或其他 Python package 复用的基础能力才下沉到 `packages/core`。
- 跨语言契约进入 `packages/contracts` 前，需要先明确源 schema、生成命令、消费者和验证方式。
- 插件能力优先落在 `plugins/` 或 `runtime/plugins` 的 Registry 边界，不通过核心代码硬编码 class、import 或 if/else 注册。

## 协作边界

- 开始开发前先确认当前分支和远程主线状态；不要在本地过期的 `main` 上继续堆提交。
- 每个 issue 使用独立分支推进，PR 范围应围绕同一个 issue 或 OpenSpec change。
- 修改前必须阅读 issue 正文和评论；评论中的约束优先纳入实现。
- 涉及行为、架构、跨模块契约或持久化边界时，先查看 `docs/design/`、`openspec/` 中相关 change 或 stable spec。
- 不把无关格式化、目录迁移、依赖升级混进同一个 PR。
- 提交保持原子化；提交信息使用中文，并按真实改动采用 Angular 规范。

## Issue 和 PR 工作流

- AI 代创建或整理 GitHub issue 时，使用 `.agents/skills/gh-issue-create`，把 discussion、设计差距、PR 评论或粗略需求压成包含 why now、范围、非目标、未决点、子任务树、验收、验证和 OpenSpec 处理的 issue。
- AI 接手 GitHub issue 时，使用 `.agents/skills/gh-issue-deliver`，先读 issue 正文、评论、关联 OpenSpec 和设计文档；影响行为、架构或契约时，先补齐或复用 `openspec/changes/<change-id>/`。
- issue 不是施工单；合格 issue 必须说明为什么现在做、这一刀收什么、明确不做什么、什么算成功、还有哪些点不能由实现者脑补。
- OpenSpec change 创建后，proposal、design、specs 和 tasks 是同一个 change 的不同收束面；不要在 change 外再维护第二套设计或任务计划。
- 新建或大幅更新 OpenSpec artifacts 后，必须先单独提交 OpenSpec-only PR 等待审核；维护者在该 PR 下明确评论“没问题”或批准前，不允许继续实现代码。
- OpenSpec-only PR 只能包含本 change 的 proposal、design、specs、tasks 和必要说明，不混入实现、依赖升级、格式化或无关文档。
- 准备创建 PR 时，使用 `.agents/skills/gh-pr-create`，PR 说明必须链接 issue/change，写清依据、改动摘要、验证结果、未验证风险和 review notes。
- 处理 PR 评论、CI 评论或 AI review 时，使用 `.agents/skills/gh-pr-comments`；逐条区分 must-fix、should-fix、needs-discussion、defer 和 not-applicable。
- AI review、Copilot review 或模型评论不是权威结论。需要用当前代码、仓库规则、已安装版本、官方文档和验证结果判断；正确的修，错误的用证据回复，不确定的做最小验证或请维护者决策。

## 配置与敏感信息

- 不提交真实 secret、token、私有策略、生产数据库地址或本地个人配置。
- `.env` 只作为本地和部署环境的配置入口；代码应允许在没有 `.env` 时加载必要默认值或清晰降级。
- 数据库连接、服务端口、运行模式等部署相关配置优先从环境变量读取，不在业务代码中写死生产值。
- 本地 Compose 可以提供开发默认值，但需要保留环境变量覆盖入口。
- API 响应、日志和测试断言不得暴露 secret 原文。

## 生成物与运行时数据

- 不提交 `__pycache__`、`.pyc`、测试缓存、构建产物、日志、运行时数据库文件或私有插件内容。
- 需要提交生成文件时，必须确认它是项目约定的源码派生产物，并且由仓库中的命令可重建。
- 不随意删除迁移文件、配置样例、设计文档、OpenSpec change 或 runtime 目录占位文件。
- 清理看似无用的文件前，先确认它不是目录保留、生成入口、迁移历史或后续模块边界。

## 代码与架构约束

- API 层只处理 HTTP、依赖注入、异常映射、路由和应用生命周期，不承载核心领域逻辑。
- 共享配置、数据库 session、迁移和跨应用基础能力优先放在 `packages/core`。
- 前端只承载管理台交互和展示，不实现后端策略判断、交易决策或权限绕过逻辑。
- 插件相关能力需要保持官方插件目录与 `runtime/plugins` 的边界：前者随代码分发，后者用于本地或私有安装。
- 插件只能通过 `plugin.yaml` 和 Registry 进入系统，不在核心代码里写死插件 class、import 列表或 if/else 注册。
- Source Plugin 只负责采集、接收和标准化原始信息，不能直接调用行业包或绕过 Event Bus。
- Agent、行业包和工具都不能绕过 AgentRuntime、ToolRegistry、Skill Registry、Decision 或 Policy Gate。
- 真实交易执行默认不是初版能力；executor 必须先支持 disabled、dry-run 或 mock，并由配置、权限、风险和人工确认共同放行。
- ORM model 只负责数据库映射，不能直接作为 API DTO、Event DTO 或 Plugin DTO 返回。
- 关键状态变化、插件生命周期、工具调用、高风险动作和人工确认必须可审计。
- 实时通道只做状态变化提醒，不作为业务状态真源；业务状态以 REST、数据库和审计记录恢复。
- 对占位 app/package 只写清晰边界，不提前创建复杂抽象或完整实现。
- 涉及较新的框架、库或 API 时，不要只依赖模型记忆；先查 lockfile、已安装版本、现有代码和官方文档，再决定 AI 建议是否适用。

## 验证与说明

- 选择与改动范围匹配的最小有效验证，不为了文档改动强行跑全量测试。
- Python、Web、Docker、数据库迁移等改动，需要选择能覆盖受影响边界的验证方式。
- Docker、Compose、数据库迁移相关改动必须至少验证配置可解析，并说明是否实际启动过服务。
- 如果验证命令缺依赖、受网络限制或本地环境不可用，最终说明中必须写清楚未验证项和原因。

## OpenSpec 边界

- 本仓库使用根目录 `openspec/`，不要创建 `docs/openspec`。
- 影响行为、架构、跨模块契约或长期边界的变更，需要关联 issue、OpenSpec change 或设计文档真源。
- 每个 PR 只绑定自己的 change，不混入无关 OpenSpec 产物。
- OpenSpec artifacts 本身需要被 review；新建或大幅更新 change 后，先提 OpenSpec-only PR，维护者在 PR 下明确评论“没问题”或批准后即可开实现 PR，不必等待该 PR 合入。
- 如果实现结果改变已归档 spec 或 `docs/design/` 的长期约定，需要在 PR 中说明，并判断是否补充新的 OpenSpec change 或更新设计文档。
